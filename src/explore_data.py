"""
K-Curator: 데이터 품질 조사
1페이지(오래된 데이터) vs 마지막 페이지(최신 데이터) 비교
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("EMUSEUM_API_KEY")
URL = "https://api.kcisa.kr/openapi/service/rest/meta/MPKreli"


def fetch_page(page_no: int, num_rows: int = 10):
    """특정 페이지의 데이터를 가져옴"""
    params = {
        "serviceKey": API_KEY,
        "numOfRows": num_rows,
        "pageNo": page_no,
    }
    response = requests.get(URL, params=params, headers={"Accept": "application/json"})
    data = response.json()
    
    if data["response"]["header"]["resultCode"] != "0000":
        return None, 0
    
    items = data["response"]["body"]["items"]["item"]
    total = int(data["response"]["body"]["totalCount"])
    return items, total


def analyze_quality(items, label: str):
    """데이터 품질 분석 + 출력"""
    print(f"\n{'='*60}")
    print(f"  📊 {label}")
    print(f"{'='*60}")
    
    if not items:
        print("  데이터 없음")
        return
    
    total = len(items)
    
    # 필드별 채워진 개수 카운트
    fields_to_check = [
        ('description', '해설'),
        ('subjectKeyword', '키워드'),
        ('subjectCategory', '분류'),
        ('temporal', '시대'),
        ('medium', '재질'),
    ]
    
    print(f"\n  [필드 채워짐 비율] (총 {total}개 중)")
    for field, label_kr in fields_to_check:
        filled = sum(1 for item in items if item.get(field))
        pct = (filled / total) * 100
        bar = '█' * int(pct / 10) + '░' * (10 - int(pct / 10))
        print(f"    {label_kr:6s} [{bar}] {filled}/{total} ({pct:.0f}%)")
    
    # 작품 제목 샘플 5개
    print(f"\n  [작품 제목 샘플]")
    for i, item in enumerate(items[:5], 1):
        title = item.get('title') or '(제목없음)'
        temporal = item.get('temporal') or '(시대불명)'
        print(f"    {i}. {title} ({temporal})")
    
    # 해설 있는 작품 1개 보여주기
    items_with_desc = [item for item in items if item.get('description')]
    if items_with_desc:
        sample = items_with_desc[0]
        desc = sample.get('description', '')[:200]
        print(f"\n  [해설 있는 작품 예시]")
        print(f"    제목: {sample.get('title') or '(없음)'}")
        print(f"    해설: {desc}...")


# ===== 메인 실행 =====
print("🔍 K-Curator 데이터 품질 조사 시작")
print(f"   API 키 길이: {len(API_KEY)}자")

# 1. 1페이지 조회
items_first, total = fetch_page(1, 10)
print(f"\n📦 전체 데이터 수: {total:,}개")

analyze_quality(items_first, "1페이지 (가장 오래된 데이터 추정)")

# 2. 마지막 페이지 조회
last_page = (total // 10) + (1 if total % 10 else 0)
items_last, _ = fetch_page(last_page, 10)
analyze_quality(items_last, f"마지막 페이지 #{last_page} (최신 데이터 추정)")

# 3. 중간 페이지 조회
middle_page = last_page // 2
items_middle, _ = fetch_page(middle_page, 10)
analyze_quality(items_middle, f"중간 페이지 #{middle_page}")

print(f"\n{'='*60}")
print("  ✅ 조사 완료!")
print(f"{'='*60}")
print("\n💰 사용한 API 호출 수: 3회 / 일일 한도 1000회")