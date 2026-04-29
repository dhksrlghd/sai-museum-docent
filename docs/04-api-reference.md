# 04. API 레퍼런스

베이스 URL (production): `https://wangihong-k-curator.hf.space`
베이스 URL (local dev): `http://127.0.0.1:8000`

## 엔드포인트 요약

| 메서드 | 경로 | 역할 | 응답 형식 |
|---|---|---|---|
| GET  | `/api/health` | 헬스체크 | JSON |
| GET  | `/api/today` | 오늘의 테마 + 추천 6점 | JSON |
| GET  | `/api/works` | 321점 카탈로그 (검색·페이지) | JSON |
| GET  | `/api/works/{id}` | 작품 1점 상세 | JSON |
| GET  | `/api/works/{id}/similar` | CLIP 닮은 작품 | JSON |
| GET  | `/api/exhibitions` | 7관 36실 + 진행중 특별전 | JSON |
| GET  | `/api/halls/{name}` | 특정 관 상세 | JSON |
| POST | `/api/chat` | RAG 챗 (3-mode) | SSE 스트림 |
| POST | `/api/plan` | 관람 코스 빌더 | SSE 스트림 |

자동 OpenAPI 문서: `/docs` (Swagger UI), `/redoc`

---

## GET /api/health

```http
GET /api/health
```

```json
{
  "ok": true,
  "collection_size": 1265,
  "modes": ["adult", "kid", "foreign"]
}
```

---

## GET /api/today

날짜 기반 결정적 큐레이션. 같은 날엔 같은 응답, 다음 날 자동 갱신.

```http
GET /api/today
```

```json
{
  "date": "2026-04-30",
  "theme": {
    "id": "letters",
    "ko": "한자와 한글",
    "en": "Hanja and Hangeul",
    "seed": "한글 훈민정음 한자 글씨"
  },
  "picks": [
    {
      "relic_id": 1234567,
      "title": "한글 금속활자",
      "subtitle": "",
      "curator": "이재정",
      "period": "조선",
      "thumbnail_url": "https://www.museum.go.kr/...",
      "score": 0.872
    }
    // ... 5 more
  ]
}
```

테마 풀은 `src/daily_pick.py`에 30개 정의. day-of-year(0~365) 기준 회전.

---

## GET /api/works

```http
GET /api/works?limit=24&offset=0&q=백자
```

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `limit` | int | 0 (전체) | 최대 반환 개수 |
| `offset` | int | 0 | 시작 인덱스 |
| `q` | string | "" | 작품명 부분 일치 검색 |

```json
{
  "total": 321,
  "offset": 0,
  "items": [
    {
      "relic_recommend_id": 2351292,
      "title_full": "<기영회도> - 세 가지 복을 누린 원로 관료들의 잔치",
      "thumbnail_url": "https://...",
      "detail_url": "https://www.museum.go.kr/..."
    }
  ]
}
```

---

## GET /api/works/{relic_id}

```http
GET /api/works/2351292
```

전체 작품 JSON 반환 (제목·부제·큐레이터·메타·본문 블록·이미지·라이선스).

```json
{
  "relic_recommend_id": 2351292,
  "source_url": "...",
  "scraped_at": "2026-04-29T14:10:33",
  "title": "〈기영회도〉",
  "subtitle": "세 가지 복을 누린 원로 관료들의 잔치",
  "curator": "오다연",
  "title_image_url": "https://...",
  "metadata": {
    "raw_caption": "작가 모름, <기영회도>, 조선 1584년, 비단에 색, ...",
    "artist": "작가 모름",
    "period": "조선 1584년",
    "medium": "비단에 색",
    "size": "163x128.5cm",
    "collection_no": "국립중앙박물관(신수14888)",
    "grade": "보물 제1328호"
  },
  "images": [
    { "url": "https://...", "caption": "작가 모름, <기영회도>, ..." }
  ],
  "body": [
    { "type": "paragraph", "text": "16세기 후반..." },
    { "type": "heading",   "text": "1584년에 열린 성대한 잔치" },
    { "type": "quote",     "text": "..." },
    { "type": "caption",   "text": "...", "image_url": "https://..." }
  ],
  "license": "국립중앙박물관이(가) 창작한 ..."
}
```

---

## GET /api/works/{relic_id}/similar

CLIP 이미지 유사도로 닮은 작품 추천.

```http
GET /api/works/2351292/similar?k=6
```

내부 동작:
1. 해당 작품의 첫 이미지 임베딩을 query로 사용
2. `kcurator_images` 컬렉션에서 cosine top-N 검색
3. 같은 작품 자기 자신 제외, 작품 단위 dedupe

```json
{
  "source_relic_id": 2351292,
  "similar": [
    {
      "relic_id": 16858,
      "title": "<호조낭관계회도>",
      "subtitle": "",
      "curator": "...",
      "period": "조선",
      "image_url": "https://...",
      "thumbnail_url": "https://...",
      "score": 0.913
    }
    // ... up to k items
  ]
}
```

이미지 컬렉션이 없으면 503 반환.

---

## GET /api/exhibitions

```http
GET /api/exhibitions
```

```json
{
  "halls": [
    {
      "name": "서화관",
      "floor": "2F",
      "rooms": [
        { "name": "외규장각 의궤", "showroom_code": "DM0028", "url": "...", "works_count": 8 }
      ]
    }
  ],
  "special": [
    {
      "exhi_id": "3056031",
      "title": "각角진 백자 이야기",
      "labels": ["현재전시", "테마전"],
      "period": "2025-08-26~2026-06-21",
      "location": "분청사기·백자실",
      "thumbnail_url": "https://...",
      "detail_url": "https://...",
      "intro": "조선 17세기부터 등장하여..."
    }
  ]
}
```

---

## GET /api/halls/{hall_name}

```http
GET /api/halls/서화관
```

해당 관의 모든 실 + 작품 리스트 전체.

```json
{
  "hall": "서화관",
  "floor": "2F",
  "rooms": [
    {
      "hall": "서화관",
      "floor": "2F",
      "room_name": "외규장각 의궤",
      "showroom_code": "DM0028",
      "intro": "...",
      "works": ["장렬왕후존숭도감의궤", "..."],
      "url": "..."
    }
  ]
}
```

---

## POST /api/chat (SSE)

3-mode RAG 챗.

```http
POST /api/chat
Content-Type: application/json

{
  "query": "기영회도가 뭐야?",
  "mode": "adult",        // adult | kid | foreign
  "k": 5
}
```

응답: `text/event-stream` (Server-Sent Events).

이벤트 타입:

| event | data | 시점 |
|---|---|---|
| `sources` | JSON 배열 | 첫 번째 — 검색 결과 출처 카드 |
| `token` | 문자열 | LLM 토큰 단위로 N회 |
| `error` | 문자열 | 실패 시 1회 |
| `done` | (빈 문자열) | 마지막 |

`sources` 페이로드 예시:
```json
[
  {
    "relic_id": 2351292,
    "title": "〈기영회도〉",
    "subtitle": "세 가지 복을 누린 원로 관료들의 잔치",
    "curator": "오다연",
    "section": "",
    "period": "조선 1584년",
    "score": 0.883,
    "thumbnail_url": "https://...",
    "detail_url": "https://..."
  }
]
```

---

## POST /api/plan (SSE)

관람 코스 빌더.

```http
POST /api/plan
Content-Type: application/json

{
  "duration_min": 60,           // 30 | 60 | 90 | 120 | 180
  "companion": "self",          // self | kid | foreign
  "interests": "조선 풍속화",
  "k": 18
}
```

내부:
1. `interests` 임베딩 → 후보 18점 (작품 단위 dedupe)
2. LLM에게 후보 + 시간/동반자 가이드 + 출력 포맷을 system+user prompt로 전달
3. 마크다운 형식 코스 응답 스트리밍

이벤트:
- `candidates` (JSON 배열) — 1회, 후보 작품 미리보기
- `token` (문자열) — N회, LLM 마크다운 토큰
- `done` — 1회

`candidates` 페이로드:
```json
[
  {
    "relic_id": 16847,
    "title": "단원풍속도첩, 김홍도",
    "subtitle": "",
    "category": "recommend",
    "hall": "",
    "floor": "",
    "location": "",
    "thumbnail_url": "https://..."
  }
]
```

LLM 출력 예시 (foreign mode):
```markdown
## Today's Course — about 60 min

A walk through Joseon-era folk paintings...

### 1. Danwon Pungsokdo Cheop, Kim Hong-do — 큐레이터 추천 (10 min)
Look at the rhythmic compositions...

→ → 1F → 2F (about 3 min walk)

### 2. ...
```

---

## 클라이언트 SSE 파싱 (frontend/src/lib/api.js)

```js
const SEP = /\r\n\r\n|\n\n|\r\r/   // 모든 EOL 변형 수용

while (true) {
  const { done, value } = await reader.read()
  if (done) break
  buffer += decoder.decode(value, { stream: true })
  let m
  while ((m = SEP.exec(buffer))) {
    const ev = parseSSE(buffer.slice(0, m.index))
    buffer = buffer.slice(m.index + m[0].length)
    handleEvent(ev)   // event/data 분기
  }
}
```

서버는 `sse-starlette`로 응답 — 이벤트 라인 끝이 `\r\n` 이라
처음에 `\n\n`만 찾던 파서가 묵묵히 무한 대기 → 정규식으로 모두 수용.
