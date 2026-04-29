"""
사이 (SAI): e뮤지엄 API 데이터 품질 조사 (v0 데이터 탐색 단계 산물).

1페이지(오래된 데이터) vs 마지막 페이지(최신) 데이터 품질 비교.

NOTE: v0 시절 의사결정의 근거가 된 스크립트 — e뮤지엄 API의 description이
"보존상태 기록" 위주임을 확인하고 큐레이터 추천 페이지 스크래핑으로
방향을 전환하게 만든 도구. 학습 여정의 흔적으로 보존됩니다.
"""

import os
import sys

import requests
from dotenv import load_dotenv

URL = "https://api.kcisa.kr/openapi/service/rest/meta/MPKreli"


def fetch_page(api_key: str, page_no: int, num_rows: int = 10):
    """특정 페이지의 데이터를 가져옴."""
    params = {"serviceKey": api_key, "numOfRows": num_rows, "pageNo": page_no}
    response = requests.get(URL, params=params, headers={"Accept": "application/json"})
    data = response.json()
    if data["response"]["header"]["resultCode"] != "0000":
        return None, 0
    items = data["response"]["body"]["items"]["item"]
    total = int(data["response"]["body"]["totalCount"])
    return items, total


def analyze_quality(items, label: str) -> None:
    """데이터 품질 분석 + 출력."""
    print(f"\n{'='*60}")
    print(f"  [{label}]")
    print(f"{'='*60}")

    if not items:
        print("  데이터 없음")
        return

    total = len(items)
    fields_to_check = [
        ("description", "해설"),
        ("subjectKeyword", "키워드"),
        ("subjectCategory", "분류"),
        ("temporal", "시대"),
        ("medium", "재질"),
    ]

    print(f"\n  필드 채워짐 비율 (총 {total}개 중)")
    for field, label_kr in fields_to_check:
        filled = sum(1 for item in items if item.get(field))
        pct = (filled / total) * 100
        bar = "#" * int(pct / 10) + "-" * (10 - int(pct / 10))
        print(f"    {label_kr:6s} [{bar}] {filled}/{total} ({pct:.0f}%)")

    print("\n  작품 제목 샘플")
    for i, item in enumerate(items[:5], 1):
        title = item.get("title") or "(제목없음)"
        temporal = item.get("temporal") or "(시대불명)"
        print(f"    {i}. {title} ({temporal})")

    items_with_desc = [item for item in items if item.get("description")]
    if items_with_desc:
        sample = items_with_desc[0]
        desc = sample.get("description", "")[:200]
        print("\n  해설 있는 작품 예시")
        print(f"    제목: {sample.get('title') or '(없음)'}")
        print(f"    해설: {desc}...")


def main() -> int:
    load_dotenv()
    api_key = os.getenv("EMUSEUM_API_KEY")
    if not api_key:
        print("EMUSEUM_API_KEY 가 .env 에 없습니다.", file=sys.stderr)
        return 1

    print("사이 — 데이터 품질 조사 시작")
    print(f"  API 키 길이: {len(api_key)}자")

    items_first, total = fetch_page(api_key, 1, 10)
    print(f"\n  전체 데이터 수: {total:,}개")
    analyze_quality(items_first, "1페이지 (가장 오래된 데이터 추정)")

    last_page = (total // 10) + (1 if total % 10 else 0)
    items_last, _ = fetch_page(api_key, last_page, 10)
    analyze_quality(items_last, f"마지막 페이지 #{last_page} (최신 데이터 추정)")

    middle_page = last_page // 2
    items_middle, _ = fetch_page(api_key, middle_page, 10)
    analyze_quality(items_middle, f"중간 페이지 #{middle_page}")

    print(f"\n{'='*60}")
    print("  조사 완료")
    print(f"{'='*60}")
    print("\n  사용한 API 호출 수: 3회 / 일일 한도 1000회")
    return 0


if __name__ == "__main__":
    sys.exit(main())
