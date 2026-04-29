"""
K-Curator: e뮤지엄 API 첫 호출 테스트
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("EMUSEUM_API_KEY")

if not API_KEY:
    raise ValueError(".env 파일에서 EMUSEUM_API_KEY를 못 찾았어요!")

print(f"API 키 로딩 성공 (길이: {len(API_KEY)}자)")

URL = "https://api.kcisa.kr/openapi/service/rest/meta/MPKreli"
params = {
    "serviceKey": API_KEY,
    "numOfRows": 5,
    "pageNo": 1,
}

print("API 호출 중...")
response = requests.get(URL, params=params, headers={"Accept": "application/json"})
print(f"응답 코드: {response.status_code}")

data = response.json()
result_code = data["response"]["header"]["resultCode"]
result_msg = data["response"]["header"]["resultMsg"]
print(f"결과: [{result_code}] {result_msg}")

if result_code != "0000":
    print("정상 응답이 아닙니다.")
    exit()

items = data["response"]["body"]["items"]["item"]
total = data["response"]["body"]["totalCount"]
print(f"전체 작품 수: {total}개")
print(f"가져온 작품: {len(items)}개")
print("")

for idx, item in enumerate(items, 1):
    print(f"--- [{idx}] ---")
    print(f"제목: {item.get('title') or '(없음)'}")
    print(f"시대: {item.get('temporal') or '(없음)'}")
    print(f"재질: {item.get('medium') or '(없음)'}")
    print(f"분류: {item.get('subjectCategory') or '(없음)'}")
    desc = item.get('description') or '(없음)'
    print(f"해설: {desc[:100]}")
    print("")