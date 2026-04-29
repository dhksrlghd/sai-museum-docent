"""
사이 (SAI): '오늘의 큐레이션' 생성기
- 날짜 기반 결정적 테마 (day-of-year) → 임베딩 검색으로 추천 작품 6점
- 별도 cron 불필요 — 같은 날엔 같은 결과, 다음 날엔 자동 갱신

api.py의 /api/today 엔드포인트가 이 모듈을 사용한다.
"""

from __future__ import annotations

import datetime
from typing import Any

# 30개 테마 풀: 매일 day-of-year 인덱싱으로 회전
THEMES: list[dict] = [
    {"id": "spring",     "ko": "봄날의 정취",          "en": "Spring's grace",            "seed": "봄 꽃 자연 풍경 매화"},
    {"id": "mountain",   "ko": "한국의 산수",          "en": "Korean landscapes",         "seed": "산수화 자연 산 강 경치"},
    {"id": "royal",      "ko": "조선 왕실의 위엄",     "en": "Joseon royal majesty",      "seed": "왕실 어진 의궤 의례 왕"},
    {"id": "buddha",     "ko": "불교의 빛",            "en": "Light of Buddhism",         "seed": "불상 사찰 불교 보살 부처"},
    {"id": "color",      "ko": "색의 미학",            "en": "The aesthetics of color",   "seed": "단청 채색 색채 화려 청록"},
    {"id": "daily",      "ko": "옛 사람들의 일상",     "en": "Old Korea's daily life",    "seed": "풍속 일상 사람 가족 농촌"},
    {"id": "ancient",    "ko": "구석기에서 통일신라까지", "en": "Prehistory to Silla",       "seed": "선사 청동 신라 백제 토기"},
    {"id": "ceramic",    "ko": "도자기 산책",          "en": "A walk through ceramics",   "seed": "백자 청자 도자기 분청사기"},
    {"id": "calligraphy","ko": "글씨와 그림",          "en": "Word and image",            "seed": "서예 글씨 한자 서화"},
    {"id": "tomb",       "ko": "무덤에서 나온 것들",   "en": "Treasures from tombs",      "seed": "고분 무덤 부장품 토용"},
    {"id": "exchange",   "ko": "외국과의 만남",        "en": "Encounters abroad",         "seed": "사신 외교 일본 중국 교류"},
    {"id": "mother",     "ko": "어머니의 손길",        "en": "A mother's hand",           "seed": "여인 가족 아이 어머니 가정"},
    {"id": "children",   "ko": "어린 마음으로",        "en": "With a child's heart",      "seed": "동물 새 강아지 고양이 아이"},
    {"id": "tiger",      "ko": "호랑이 이야기",        "en": "Tales of tigers",           "seed": "호랑이 산신 민화"},
    {"id": "quiet",      "ko": "고요한 풍경",          "en": "Stillness",                 "seed": "조용 명상 사유 정적 한적"},
    {"id": "minhwa",     "ko": "민중의 그림",          "en": "Folk paintings",            "seed": "민화 민중 풍속 일상"},
    {"id": "uigwe",      "ko": "화려한 의궤",          "en": "Splendid Uigwe",            "seed": "의궤 외규장각 의례 행렬"},
    {"id": "record",     "ko": "보물의 기록",          "en": "Records of treasures",      "seed": "보물 국보 등록문화재 국가유산"},
    {"id": "nature",     "ko": "자연과 짐승",          "en": "Beasts and nature",         "seed": "동물 호랑이 새 짐승 화훼"},
    {"id": "baekja",     "ko": "백자의 단아함",        "en": "Grace of white porcelain",  "seed": "백자 달항아리 청화백자"},
    {"id": "celadon",    "ko": "청자의 비취",          "en": "Jade of celadon",           "seed": "고려청자 비취 상감"},
    {"id": "metal",      "ko": "금속에 새긴 마음",     "en": "Metal craft of devotion",   "seed": "금속공예 청동 금동 향로"},
    {"id": "smile",      "ko": "부처의 미소",          "en": "Buddha's smile",            "seed": "반가사유상 미륵 보살 불상"},
    {"id": "taoist",     "ko": "신선의 세계",          "en": "World of immortals",        "seed": "신선 도교 산수 무릉도원"},
    {"id": "stars",      "ko": "별과 우주",            "en": "Stars and cosmos",          "seed": "천문 성좌 별자리 하늘"},
    {"id": "letters",    "ko": "한자와 한글",          "en": "Hanja and Hangeul",         "seed": "한글 훈민정음 한자 글씨"},
    {"id": "lost",       "ko": "잊힌 이름들",          "en": "Forgotten names",           "seed": "장인 화원 이름 작가 모름"},
    {"id": "lotus",      "ko": "연꽃의 향기",          "en": "Fragrance of lotus",        "seed": "연꽃 불교 정원 청자 연못"},
    {"id": "plum",       "ko": "매화와 대나무",        "en": "Plum and bamboo",           "seed": "매화 대나무 사군자 묵화"},
    {"id": "scholar",    "ko": "학문의 길",            "en": "The path of learning",      "seed": "학자 선비 사대부 책 글"},
]


def today_theme(now: datetime.date | None = None) -> dict:
    today = now or datetime.date.today()
    idx = today.toordinal() % len(THEMES)
    return THEMES[idx]


def all_themes() -> list[dict]:
    return list(THEMES)


def picks_for_theme(
    theme: dict,
    model: Any,
    coll: Any,
    thumbnails: dict,
    query_prefix: str = "query: ",
    n: int = 6,
) -> list[dict]:
    """테마 시드 쿼리로 추천 작품 N점 (작품 단위 dedupe)."""
    seed = theme["seed"]
    emb = model.encode([query_prefix + seed], normalize_embeddings=True)[0]
    res = coll.query(
        query_embeddings=[emb.tolist()],
        n_results=n * 4,
        include=["documents", "metadatas", "distances"],
    )
    seen: set = set()
    picks: list[dict] = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        # 추천 카테고리 작품만 (큐레이터 본문이 풍부)
        if meta.get("category") not in ("recommend", "", None):
            continue
        rid = meta.get("relic_id") or 0
        if rid in seen or not rid:
            continue
        seen.add(rid)
        thumb = thumbnails.get(rid, {})
        picks.append(
            {
                "relic_id": rid,
                "title": meta.get("title", ""),
                "subtitle": meta.get("subtitle", ""),
                "curator": meta.get("curator", ""),
                "period": meta.get("period", ""),
                "thumbnail_url": thumb.get("thumbnail_url", ""),
                "score": round(1.0 - dist, 3),
            }
        )
        if len(picks) >= n:
            break
    return picks
