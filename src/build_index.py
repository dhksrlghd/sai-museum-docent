"""
K-Curator: 본문 청킹 + 임베딩 + Chroma 인덱스 구축
- 입력: data/raw/relic_*.json (321건)
- 청킹: heading 단위 섹션. heading 등장 전의 도입부는 'intro' 섹션.
- 임베딩: intfloat/multilingual-e5-small (passage: 프리픽스 사용)
- 출력:
    data/processed/chunks.jsonl  (사람이 읽을 수 있는 청크 덤프)
    data/chroma/                 (Chroma persistent 디렉토리)

사용법:
    python src/build_index.py            # 전체 빌드
    python src/build_index.py --dry      # 청킹만 하고 임베딩/저장은 스킵
"""

import argparse
import glob
import json
import sys
import time
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma"

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
COLLECTION = "kcurator_relics"

# e5는 입력에 'passage: ' / 'query: ' 프리픽스를 요구함
PASSAGE_PREFIX = "passage: "
QUERY_PREFIX = "query: "

# e5-small 한계: 512 tokens. 한국어 약 1.5~2 tok/자 → 1500자에서 자르는 게 안전.
MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CHARS = 100


def load_relics() -> list[dict]:
    files = sorted(glob.glob(str(RAW_DIR / "relic_*.json")))
    files = [f for f in files if "relic_list" not in f]
    relics = []
    for f in files:
        with open(f, encoding="utf-8") as fp:
            relics.append(json.load(fp))
    return relics


def chunk_relic(relic: dict) -> list[dict]:
    """본문을 heading 단위 섹션으로 묶는다.

    각 섹션 청크는:
      - 텍스트 = '{작품제목} - {부제}\\n[{섹션제목}]\\n{본문 결합}'
      - 메타 = {relic_id, title, curator, section, period, medium, grade, ...}
    """
    body = relic.get("body") or []
    if not body:
        return []

    title = relic.get("title", "")
    subtitle = relic.get("subtitle", "")
    full_title = f"{title} - {subtitle}" if subtitle else title
    md = relic.get("metadata") or {}

    # heading 위치를 찾아 섹션 범위 분할
    heading_idx = [i for i, b in enumerate(body) if b["type"] == "heading"]
    if not heading_idx:
        # heading이 없는 작품: 전체를 단일 섹션으로
        section_ranges = [("intro", 0, len(body))]
    else:
        section_ranges = []
        if heading_idx[0] > 0:
            # 첫 heading 이전의 도입부
            section_ranges.append(("intro", 0, heading_idx[0]))
        for i, hi in enumerate(heading_idx):
            end = heading_idx[i + 1] if i + 1 < len(heading_idx) else len(body)
            section_ranges.append((body[hi]["text"], hi, end))

    base_meta = {
        "relic_id": relic["relic_recommend_id"],
        "title": title,
        "subtitle": subtitle,
        "curator": relic.get("curator", ""),
        "period": md.get("period", ""),
        "medium": md.get("medium", ""),
        "grade": md.get("grade", ""),
        "source_url": relic.get("source_url", ""),
    }

    chunks = []
    chunk_seq = 0
    for sec_name, start, end in section_ranges:
        first = body[start]
        block_iter = body[start + 1 : end] if first["type"] == "heading" else body[start:end]

        # paragraph/quote/caption 단위 텍스트 리스트
        parts: list[str] = []
        for blk in block_iter:
            txt = blk.get("text", "").strip()
            if not txt:
                continue
            if blk["type"] == "quote":
                parts.append(f"“{txt}”" if not txt.startswith("“") else txt)
            else:
                parts.append(txt)

        if not parts:
            continue

        section_label = sec_name if sec_name != "intro" else ""

        # 긴 섹션은 paragraph 경계에서 sub-chunk로 분할
        for piece_text in _pack_parts(parts, MAX_CHUNK_CHARS):
            header = f"{full_title}"
            if section_label:
                header += f"\n[{section_label}]"
            chunk_text = f"{header}\n{piece_text}"

            if len(chunk_text) < MIN_CHUNK_CHARS:
                continue

            chunks.append(
                {
                    "id": f"{relic['relic_recommend_id']}-{chunk_seq}",
                    "text": chunk_text,
                    "metadata": {**base_meta, "section": section_label},
                }
            )
            chunk_seq += 1
    return chunks


def _pack_parts(parts: list[str], max_chars: int) -> list[str]:
    """문단(parts)을 max_chars 안에 들어가게 패킹한다.
    각 문단 자체가 max_chars를 넘으면 그 문단만 단독으로 한 청크가 된다.
    """
    out: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for p in parts:
        p_len = len(p) + 1  # 줄바꿈 1자 가산
        if cur and cur_len + p_len > max_chars:
            out.append("\n".join(cur).strip())
            cur, cur_len = [], 0
        cur.append(p)
        cur_len += p_len
    if cur:
        out.append("\n".join(cur).strip())
    return out


def build_chunks(relics: list[dict]) -> list[dict]:
    chunks = []
    for r in relics:
        chunks.extend(chunk_relic(r))
    return chunks


def write_jsonl(path: Path, items: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def index_chunks(chunks: list[dict]) -> None:
    """sentence-transformers + Chroma persistent client로 인덱싱."""
    from sentence_transformers import SentenceTransformer
    import chromadb

    print(f"[build_index] 임베딩 모델 로드: {EMBEDDING_MODEL}")
    t0 = time.time()
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"[build_index] 모델 로드 완료 ({time.time()-t0:.1f}초)")

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # 기존 컬렉션 있으면 지우고 새로 만든다 (재인덱싱 안전)
    try:
        client.delete_collection(COLLECTION)
        print(f"[build_index] 기존 컬렉션 '{COLLECTION}' 삭제")
    except Exception:
        pass
    coll = client.create_collection(name=COLLECTION, metadata={"hnsw:space": "cosine"})

    BATCH = 64
    n = len(chunks)
    print(f"[build_index] 임베딩 시작: 총 {n}개 청크, batch={BATCH}")
    t0 = time.time()
    for i in range(0, n, BATCH):
        batch = chunks[i : i + BATCH]
        passages = [PASSAGE_PREFIX + c["text"] for c in batch]
        embs = model.encode(passages, show_progress_bar=False, normalize_embeddings=True)
        coll.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
            embeddings=embs.tolist(),
        )
        done = min(i + BATCH, n)
        print(f"  진행: {done}/{n}  ({done*100//n}%)")
    print(f"[build_index] 인덱싱 완료 ({time.time()-t0:.1f}초)")
    print(f"[build_index] Chroma 컬렉션 크기: {coll.count()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="청킹 통계만 보고 종료")
    args = ap.parse_args()

    relics = load_relics()
    print(f"[build_index] 로드한 작품: {len(relics)}건")

    chunks = build_chunks(relics)
    print(f"[build_index] 생성된 청크: {len(chunks)}개")

    if chunks:
        char_counts = [len(c["text"]) for c in chunks]
        print(
            f"[build_index] 청크 길이: min={min(char_counts)} "
            f"avg={sum(char_counts)//len(char_counts)} "
            f"max={max(char_counts)}자"
        )

    write_jsonl(PROCESSED_DIR / "chunks.jsonl", chunks)
    print(f"[build_index] 청크 덤프 저장: {PROCESSED_DIR/'chunks.jsonl'}")

    if args.dry:
        print("[build_index] --dry 모드: 임베딩/색인 생략")
        return 0

    index_chunks(chunks)
    print(f"[build_index] Chroma 디렉토리: {CHROMA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
