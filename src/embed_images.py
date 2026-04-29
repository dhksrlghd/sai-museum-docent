"""
K-Curator: 작품 이미지 CLIP 임베딩 → Chroma 인덱스
- 입력: data/raw/relic_*.json 의 images[] 필드 (1,400+장)
- 모델: sentence-transformers/clip-ViT-B-32-multilingual-v1 (한국어 텍스트도 같은 공간)
- 출력: data/chroma/ 에 'kcurator_images' 컬렉션

용도:
  - 작품-작품 유사도 (work detail의 '비슷한 작품')
  - 텍스트 → 이미지 검색 ("푸른 바다 그림")
  - (옵션) 사용자 업로드 이미지 → 비슷한 박물관 소장품

CPU에서 약 5~10분.
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma"

CLIP_MODEL = "sentence-transformers/clip-ViT-B-32"
# multilingual-v1은 텍스트 전용. 이미지 인코딩에는 표준 CLIP 사용.
# 한국어 텍스트→이미지 검색이 필요하면 multilingual 텍스트 인코더를 별도로 같이 띄워야 한다.
COLLECTION = "kcurator_images"

USER_AGENT = "Mozilla/5.0 (K-Curator portfolio scraper)"
DOWNLOAD_TIMEOUT = 12
MAX_PER_WORK = 3  # 작품당 최대 N장 (대표 이미지 위주)


def load_works() -> list[dict]:
    files = sorted(glob.glob(str(RAW_DIR / "relic_*.json")))
    files = [f for f in files if "relic_list" not in f]
    return [json.load(open(f, encoding="utf-8")) for f in files]


def collect_image_records(works: list[dict]) -> list[dict]:
    """각 작품에서 임베딩 대상 이미지 메타 리스트 추출."""
    out: list[dict] = []
    for w in works:
        rid = w["relic_recommend_id"]
        title = w.get("title", "")
        subtitle = w.get("subtitle", "")
        curator = w.get("curator", "")
        period = (w.get("metadata") or {}).get("period", "")
        imgs = w.get("images") or []
        for i, img in enumerate(imgs[:MAX_PER_WORK]):
            url = img.get("url", "")
            if not url:
                continue
            out.append(
                {
                    "id": f"{rid}-img-{i}",
                    "relic_id": rid,
                    "image_index": i,
                    "url": url,
                    "caption": img.get("caption", "") or "",
                    "title": title,
                    "subtitle": subtitle,
                    "curator": curator,
                    "period": period,
                }
            )
    return out


def fetch_image_bytes(url: str) -> bytes | None:
    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Referer": "https://www.museum.go.kr/"},
            timeout=DOWNLOAD_TIMEOUT,
        )
        if r.status_code == 200 and r.content:
            return r.content
    except Exception:
        return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="개발용: 처음 N개만 처리")
    args = ap.parse_args()

    print(f"[embed_images] CLIP 모델 로드: {CLIP_MODEL}")
    from sentence_transformers import SentenceTransformer
    from PIL import Image
    import chromadb

    t0 = time.time()
    model = SentenceTransformer(CLIP_MODEL)
    print(f"[embed_images] 모델 로드 완료 ({time.time()-t0:.1f}초)")

    works = load_works()
    records = collect_image_records(works)
    if args.limit:
        records = records[: args.limit]
    print(f"[embed_images] 작품 {len(works)}건 / 임베딩 대상 이미지 {len(records)}장")

    # Chroma collection 재생성
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION)
        print(f"[embed_images] 기존 컬렉션 '{COLLECTION}' 삭제")
    except Exception:
        pass
    coll = client.create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    BATCH = 16
    n = len(records)
    failed = 0
    t0 = time.time()
    DL_WORKERS = 8  # 동시에 N개 이미지 다운로드 (총 시간 단축)
    for i in range(0, n, BATCH):
        batch = records[i : i + BATCH]
        # 1) 다운로드 (병렬)
        with ThreadPoolExecutor(max_workers=DL_WORKERS) as pool:
            payloads = list(pool.map(fetch_image_bytes, [r["url"] for r in batch]))

        images = []
        valid: list[dict] = []
        for r, data in zip(batch, payloads):
            if not data:
                failed += 1
                continue
            try:
                img = Image.open(io.BytesIO(data)).convert("RGB")
                images.append(img)
                valid.append(r)
            except Exception:
                failed += 1
        if not images:
            print(f"  [{i+len(batch)}/{n}] (전부 실패, skip)", flush=True)
            continue
        # 2) 인코딩
        embs = model.encode(images, show_progress_bar=False, normalize_embeddings=True)
        # 3) 저장
        coll.add(
            ids=[r["id"] for r in valid],
            metadatas=[
                {
                    "relic_id": r["relic_id"],
                    "image_index": r["image_index"],
                    "url": r["url"],
                    "caption": r["caption"],
                    "title": r["title"],
                    "subtitle": r["subtitle"],
                    "curator": r["curator"],
                    "period": r["period"],
                }
                for r in valid
            ],
            embeddings=embs.tolist(),
            documents=[r["caption"] or r["title"] for r in valid],
        )
        done = min(i + BATCH, n)
        print(
            f"  [{done}/{n}] ({done*100//n}%)  "
            f"성공 {coll.count()} / 실패 {failed}  "
            f"({time.time()-t0:.0f}초 경과)",
            flush=True,
        )

    print(
        f"\n[embed_images] 완료: 인덱스 {coll.count()}장 / 실패 {failed}장 / "
        f"총 {time.time()-t0:.1f}초",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
