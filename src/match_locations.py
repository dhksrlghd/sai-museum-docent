"""
K-Curator: 추천 작품 ↔ 상설 작품 매칭
- 추천 321점의 작품 제목과 상설 643점의 작품명을 비교
- 매칭되면 추천 작품에도 hall/floor/room_name 위치 메타를 부착
- 출력: data/raw/relic_locations.json (relic_id → location 매핑)
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def normalize_title(t: str) -> str:
    """작품명 비교용 정규화: 괄호·기호·공백 제거 + 한자/한글 보존."""
    if not t:
        return ""
    # 괄호 안 부가 설명 제거: 〈〉 《》 『』 「」 () <>
    t = re.sub(r"[〈〉《》『』「」（）()<>]", "", t)
    # 부제 구분자 제거
    t = re.sub(r"\s*[-–—:·•]\s*", "", t)
    # 모든 공백 제거
    t = re.sub(r"\s+", "", t)
    return t


def main() -> int:
    # 1) 추천 작품 로드
    relic_files = sorted(glob.glob(str(RAW_DIR / "relic_*.json")))
    relic_files = [f for f in relic_files if "relic_list" not in f]
    recommends = []
    for f in relic_files:
        d = json.load(open(f, encoding="utf-8"))
        recommends.append(
            {
                "relic_id": d["relic_recommend_id"],
                "title": d.get("title", ""),
                "subtitle": d.get("subtitle", ""),
                "norm": normalize_title(d.get("title", "")),
            }
        )

    # 2) 상설 작품 로드 (실별 작품명 + 위치)
    perm = json.load(open(RAW_DIR / "permanent.json", encoding="utf-8"))
    perm_works: list[dict] = []
    for room in perm["rooms"]:
        loc = {
            "hall": room["hall"],
            "floor": room["floor"],
            "room_name": room["room_name"],
        }
        for w in room["works"]:
            perm_works.append({"title": w, "norm": normalize_title(w), **loc})

    print(f"추천 작품: {len(recommends)}점 / 상설 작품: {len(perm_works)}점")

    # 3) 매칭: 정규화된 제목 사이의 substring 양방향 검사 (짧은 한글 키워드라도 잡힘)
    matched: dict[int, dict] = {}
    for r in recommends:
        if not r["norm"] or len(r["norm"]) < 2:
            continue
        for p in perm_works:
            if not p["norm"]:
                continue
            # 정확 일치 / 한쪽이 다른 쪽 substring
            if (
                r["norm"] == p["norm"]
                or (len(r["norm"]) >= 4 and r["norm"] in p["norm"])
                or (len(p["norm"]) >= 4 and p["norm"] in r["norm"])
            ):
                matched[r["relic_id"]] = {
                    "matched_title": p["title"],
                    "hall": p["hall"],
                    "floor": p["floor"],
                    "room_name": p["room_name"],
                }
                break

    print(f"매칭 성공: {len(matched)}점 ({len(matched)*100//len(recommends)}%)")

    # 4) 저장
    out_path = RAW_DIR / "relic_locations.json"
    out = {
        "scraped_at": "(matched from permanent + recommend)",
        "matched": matched,
        "stats": {
            "total_recommends": len(recommends),
            "total_permanent_works": len(perm_works),
            "matched": len(matched),
        },
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"저장: {out_path}")

    # 샘플 출력
    print("\n매칭 샘플 5건:")
    for rid, m in list(matched.items())[:5]:
        # 추천 작품 제목 찾기
        rec = next(r for r in recommends if r["relic_id"] == rid)
        print(f"  {rid:>10}  {rec['title'][:40]:40s} → {m['hall']} {m['floor']} {m['room_name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
