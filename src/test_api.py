"""
사이 (SAI): e뮤지엄 API 첫 호출 테스트 (v0 데이터 탐색 단계 산물).

NOTE: 이 스크립트는 v0 시절 데이터 품질 조사 도구입니다.
사이의 본 운영(상세 작품 본문은 큐레이터 추천 페이지 스크래핑으로 확보)에는
사용되지 않으며, 학습 여정의 흔적으로 보존됩니다.
"""

import os
import sys

import requests
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    api_key = os.getenv("EMUSEUM_API_KEY")
    if not api_key:
        print(
            ".env 파일에서 EMUSEUM_API_KEY를 못 찾았어요. "
            "KCISA 발급 키를 .env에 추가하세요.",
            file=sys.stderr,
        )
        return 1

    print(f"API 키 로딩 성공 (길이: {len(api_key)}자)")

    url = "https://api.kcisa.kr/openapi/service/rest/meta/MPKreli"
    params = {"serviceKey": api_key, "numOfRows": 5, "pageNo": 1}

    print("API 호출 중...")
    response = requests.get(url, params=params, headers={"Accept": "application/json"})
    print(f"응답 코드: {response.status_code}")

    data = response.json()
    result_code = data["response"]["header"]["resultCode"]
    result_msg = data["response"]["header"]["resultMsg"]
    print(f"결과: [{result_code}] {result_msg}")
    if result_code != "0000":
        print("정상 응답이 아닙니다.")
        return 2

    items = data["response"]["body"]["items"]["item"]
    total = data["response"]["body"]["totalCount"]
    print(f"전체 작품 수: {total}개  /  가져온 작품: {len(items)}개\n")

    for idx, item in enumerate(items, 1):
        print(f"--- [{idx}] ---")
        print(f"제목: {item.get('title') or '(없음)'}")
        print(f"시대: {item.get('temporal') or '(없음)'}")
        print(f"재질: {item.get('medium') or '(없음)'}")
        print(f"분류: {item.get('subjectCategory') or '(없음)'}")
        desc = item.get("description") or "(없음)"
        print(f"해설: {desc[:100]}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
