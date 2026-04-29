# 03. 데이터 파이프라인

## 전체 흐름

```
┌────────────────────────────────────────────────────────────────────┐
│                       원천 (museum.go.kr)                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ 큐레이터 추천     │  │ 상설전시 7관 39실  │  │ 특별전 5건         │ │
│  │ 321점 페이지      │  │ 작품 643점        │  │  (현재 진행)      │ │
│  └─────────┬────────┘  └─────────┬────────┘  └─────────┬────────┘  │
└────────────┼─────────────────────┼─────────────────────┼───────────┘
             │ scrape_list +       │ scrape_permanent    │ scrape_special
             │ scrape_all          │                     │
             ▼                     ▼                     ▼
       relic_*.json          permanent.json        special.json
       (321 파일)             (단일 파일)            (단일 파일)
             │                     │                     │
             └────────────┬────────┴────────────┬────────┘
                          │                     │
                          │  match_locations.py │
                          ▼                     │
                relic_locations.json (52건)     │
                          │                     │
                          ▼                     ▼
                  ┌─────────────────────────────────────┐
                  │       build_index.py                │
                  │   (text 청킹 → e5-small 임베딩)      │
                  └─────────────────┬───────────────────┘
                                    ▼
                       Chroma  ·  kcurator_relics  (1,265 청크)

                  ┌─────────────────────────────────────┐
                  │       embed_images.py               │
                  │   (PIL 다운로드 → CLIP 임베딩)       │
                  └─────────────────┬───────────────────┘
                                    ▼
                       Chroma  ·  kcurator_images  (733 임베딩)
```

## 단계별 상세

### 1) 원천 페이지 분석

박물관 사이트 `https://www.museum.go.kr/MUSEUM/contents/M0501000000.do`
**큐레이터 추천 소장품** 섹션:

- 총 **321건** (33페이지, 페이지당 10건)
- URL 패턴
  - 리스트: `?cp={page}&searchId=recommend&relicRecommendUse=Y`
  - 상세: `?schM=view&relicRecommendId={id}`
- 이미지 패턴: `https://www.museum.go.kr/files/zin/curator_{n}_{i}.jpg`
- **공공누리 3유형(출처표시+변경금지)** 라이선스

상설전시 페이지 분석:
- 7관 → 각 관 안에 4~10개 실
- URL 패턴: `?showHallId={id}&showroomCode=DM00xx`
- 각 실 페이지에 "전시품" 리스트 (작품명만, 상세 페이지 링크 없음)

특별전 페이지 분석:
- 리스트 카드: `<li class="card">` 안에 제목·기간·장소·썸네일
- 상세 URL: `?exhiSpThemId={id}`

### 2) 스크래핑 (Step 1~5)

#### `scrape_list.py` — ID 리스트 (단일 요청)
처음엔 33페이지를 1.5초씩 돌려고 했는데, `pageSize=500` 파라미터로 **한 번에 321건 전체 응답** 가능하다는 걸 발견.
1초 안에 끝남.

#### `scrape_all.py` — 작품 본문 일괄 수집
- `relic_list.json`을 입력으로 받아 각 ID별 상세 페이지를 1.5초 간격으로 순회
- 이미 저장된 파일은 skip (중간 재시작 가능)
- 각 작품 1개당 추출 항목:
  - 제목·부제·큐레이터명 (이미지 alt 분석)
  - 메타데이터 (작가·시대·재질·크기·소장번호·등급)
  - 본문 블록 (heading / paragraph / quote / caption)
  - 이미지 URL + 캡션
  - 라이선스 텍스트
- 약 13분 소요, 321/321 성공

#### `scrape_permanent.py` — 상설전시
- 7관 entry URL부터 시작 → 각 관의 좌측 메뉴에서 실 URL 발견
- 각 실 페이지에서:
  - 실 소개 텍스트 (한국어 비율 필터로 alt 텍스트·반복 안내 제거)
  - "전시품" 섹션의 작품명 리스트
- 결과: 36실 / 643점 / 23,314자 소개 텍스트

#### `scrape_special.py` — 특별·테마전
- 현재 전시 리스트 페이지에서 5건 발견
- 각 상세 페이지에서 본문 단락 수집 (50자 이상, 네비/메뉴 제외)
- 결과: 5건 / 3,429자 본문

### 3) 매칭 (Step 5)

`match_locations.py`는 추천 작품 321점과 상설 작품 643점의 제목을 정규화 후 fuzzy match:
- 정규화: 괄호·구분기호·공백 제거 (`〈기영회도〉` → `기영회도`)
- 매칭: 정확 일치 OR 한쪽이 다른 쪽 substring (≥4자)

결과: **52점 (16%)** 의 추천 작품에 hall/floor/room_name 메타 부착.
나머지 84%는 "큐레이터가 추천하지만 현재 비전시" 또는 매칭 실패 (제목이 너무 다름).

이 위치 메타는 코스 빌더 `/api/plan`이 동선 계산에 활용합니다.

### 4) 청킹 + 임베딩 (Step 6)

#### 청킹 전략 (`build_index.py`)

| 카테고리 | 청크 단위 | 이유 |
|---|---|---|
| 추천 작품 (recommend) | heading 단위 섹션 → 1500자 초과 시 paragraph 경계로 분할 | 큐레이터 본문이 heading으로 자연스럽게 섹션 구분됨 |
| 상설 실 (permanent) | 실 단위 (소개 + 작품 리스트) → 길면 분할 | 실 컨텍스트가 검색 단위로 의미 있음 |
| 특별전 (special) | 전시 단위 | 5건뿐이라 분할 거의 안 됨 |

**핵심 헬퍼**: `_pack_parts(parts, max_chars)` — paragraph 경계에서 1,500자에 맞춰 패킹.
한 paragraph가 단독으로 1,500자 초과면 자르지 않고 단독 청크 (의미 보존).

청크 통계:
- 총 1,265개
- 평균 957자
- min 103자 / max 2,486자

#### 임베딩 모델 선택

`intfloat/multilingual-e5-small`:
- 384-dim, 118MB
- E5 학습 방식 — `passage: ` / `query: ` 프리픽스 필수
- 한국어 retrieval 품질 검증됨 (top-1 cosine 0.86~0.91 범위)
- bge-m3 대비 가벼워 무료 CPU 환경에 적합

#### 메타데이터 표준화

모든 청크가 동일한 키 셋을 가지도록 `EMPTY_META` 베이스를 정의 후 카테고리별로 채움:

```python
EMPTY_META = {
    "category": "",       # recommend | permanent | special
    "title": "",
    "subtitle": "",
    "curator": "",
    "section": "",        # heading 텍스트
    "period": "",
    "medium": "",
    "grade": "",
    "hall": "",           # 전시 위치 (있을 때만)
    "floor": "",
    "room_name": "",
    "location": "",
    "labels": "",
    "thumbnail_url": "",
    "source_url": "",
    "relic_id": 0,
    "exhi_id": "",
}
```

Chroma는 일관된 스키마를 좋아하기 때문에 모든 키를 빈값이라도 채워둠.

### 5) 이미지 임베딩 (Step 7)

`embed_images.py`:
- 작품당 최대 3장 → 894장 시도
- `ThreadPoolExecutor(8)`로 병렬 다운로드 (직렬 대비 5배 빠름)
- 다운로드 실패한 161장은 skip (museum.go.kr이 일부 hot-link 차단)
- CLIP-ViT-B-32 (512-dim)으로 인코딩
- 결과: **733장 인덱싱** / 약 7분 소요

## 인덱스 통계 한눈에

```
kcurator_relics  (텍스트, e5-small 384-dim, cosine)
├─ recommend  : 1,213 chunks  (321 작품)
├─ permanent  :    47 chunks  (36 실)
└─ special    :     5 chunks  (5 전시)

kcurator_images  (이미지, CLIP-B/32 512-dim, cosine)
└─ 733 embeddings  (작품당 ~2.3장 평균)
```

## 흥미로운 디테일

### 줄바꿈 정규화의 함정
초기 SSE 파서가 `\n\n`만 인식해서 토큰이 화면에 안 떴어요.
sse-starlette는 사실 `\r\n\r\n`을 보냅니다. 정규식 `\r\n\r\n|\n\n|\r\r`로 모두 수용하도록 수정.

### 한국어 비율 필터
상설전 페이지 파싱에서 영어 alt 텍스트(`'산수' 동영상의 대체텍스트입니다...`)가 본문에 섞임.
한글(가-힣) 비율 ≥ 55% 인 단락만 채택해서 제거.
→ 소개 텍스트 2,994자 → **23,314자 (8배)**.

### CLIP 모델 선택의 함정
처음엔 `clip-ViT-B-32-multilingual-v1`을 시도. 한국어 텍스트→이미지 검색이 가능할 줄 알았는데
이 모델은 **텍스트 인코더만** 다국어로 갈아끼운 것이라 이미지 인코딩이 불가능했어요.
표준 `clip-ViT-B-32`로 변경 — 이미지+영어 텍스트만 지원하지만, 우리 핵심 use case
(이미지→이미지 유사도)에는 충분.

### 호스트 측 Hot-link 차단
museum.go.kr은 일부 이미지를 외부 도메인 fetch 시 onerror placeholder(돋보기 PNG)로 응답.
Referer 헤더를 박물관 본 URL로 위장해도 18%는 막힘.
**`<img onError={hide}>`** 와 fallback caption만으로 대응. 합법적 우회는 추후 과제.
