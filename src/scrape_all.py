"""
K-Curator: 전체 큐레이터 추천 작품 자동 스크래핑
- 입력: data/raw/relic_list.json (scrape_list.py 결과)
- 동작: 각 ID마다 scrape_one.scrape() 호출 → data/raw/relic_{ID}.json 저장
- 이미 저장된 파일은 스킵하므로 중간 재시작 가능
- 사용법:
    python src/scrape_all.py            # 전체 321건
    python src/scrape_all.py 5          # 처음 5건만 (스모크 테스트)
    python src/scrape_all.py 5 --force  # 기존 파일 무시하고 5건 재수집
"""

import json
import sys
import time
from pathlib import Path

from scrape_one import RAW_DIR, save, scrape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIST_PATH = PROJECT_ROOT / "data" / "raw" / "relic_list.json"

REQUEST_DELAY_SEC = 1.5  # CLAUDE.md 권장: 요청 간 1~2초


def load_id_list() -> list[int]:
    if not LIST_PATH.exists():
        raise FileNotFoundError(
            f"{LIST_PATH} 가 없습니다. 먼저 scrape_list.py를 실행하세요."
        )
    with LIST_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return [it["relic_recommend_id"] for it in data["items"]]


def already_saved(relic_id: int) -> bool:
    return (RAW_DIR / f"relic_{relic_id}.json").exists()


def parse_args(argv: list[str]) -> tuple[int | None, bool]:
    """간단한 인자 파싱: [limit] [--force]"""
    limit: int | None = None
    force = False
    for a in argv:
        if a == "--force":
            force = True
        else:
            try:
                limit = int(a)
            except ValueError:
                print(f"[scrape_all] 알 수 없는 인자: {a}", file=sys.stderr)
                sys.exit(64)
    return limit, force


def main() -> int:
    limit, force = parse_args(sys.argv[1:])

    ids = load_id_list()
    if limit is not None:
        ids = ids[:limit]

    total = len(ids)
    print(f"[scrape_all] 대상 작품 수: {total} (force={force})")

    ok, skipped, failed = 0, 0, 0
    failures: list[tuple[int, str]] = []
    started = time.time()

    for idx, rid in enumerate(ids, 1):
        if not force and already_saved(rid):
            skipped += 1
            print(f"  [{idx:3d}/{total}] {rid}  skip (이미 있음)")
            continue

        try:
            data = scrape(rid)
            save(data)
            ok += 1
            title = (data.get("title") or "")[:30]
            curator = data.get("curator") or "?"
            print(f"  [{idx:3d}/{total}] {rid}  ok    {curator} | {title}")
        except Exception as e:  # 네트워크/파싱/저장 모두 포괄
            failed += 1
            failures.append((rid, repr(e)))
            print(f"  [{idx:3d}/{total}] {rid}  FAIL  {e}", file=sys.stderr)

        # 마지막 요청 뒤엔 sleep 불필요
        if idx < total:
            time.sleep(REQUEST_DELAY_SEC)

    elapsed = time.time() - started
    print()
    print("=" * 60)
    print(f"  완료: 성공 {ok} / 스킵 {skipped} / 실패 {failed}")
    print(f"  소요: {elapsed:.1f}초")
    if failures:
        print("  실패 목록:")
        for rid, err in failures[:20]:
            print(f"    - {rid}: {err}")
        if len(failures) > 20:
            print(f"    ... 외 {len(failures) - 20}건")
    print("=" * 60)

    return 0 if failed == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
