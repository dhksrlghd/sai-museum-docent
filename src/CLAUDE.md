# K-Curator 프로젝트 — 진행 상황 인수인계

## 프로젝트 개요
국립중앙박물관 소장품 기반 AI 도슨트 챗봇 (포트폴리오용 사이드 프로젝트).
RAG + 멀티모달 + 사용자 적응형 톤 조절(어린이/성인/외국인)이 차별점.

상세 기획은 `docs/K-Curator_프로젝트_정리.md` 참고.

## 환경
- OS: Windows 11
- Python 3.13.12 (시스템 PATH 등록됨)
- 가상환경: `C:\K-Curator\.venv`
- 활성화 명령: `.\.venv\Scripts\Activate.ps1`
- 설치된 라이브러리: requests, python-dotenv, beautifulsoup4, lxml,
  chromadb, sentence-transformers (torch CPU 포함), openai
- API 키 (.env):
    - `EMUSEUM_API_KEY` — 36자, KCISA 발급
    - `OPENAI_API_KEY` — sk-proj-... 약 160자 (RAG LLM 생성용)
- LLM: OpenAI gpt-4o-mini (Anthropic API 미사용, 사용자 결제 환경 고려)

## 현재까지 진행한 것

### 1. e뮤지엄 OpenAPI 발급 완료
- 문화포털(KCISA)에서 발급
- 일 1,000건 한도 (개발 계정)

### 2. 첫 API 호출 성공 (`src/test_api.py`)
- 엔드포인트: `https://api.kcisa.kr/openapi/service/rest/meta/MPKreli`
- 파라미터: serviceKey, numOfRows, pageNo
- 전체 데이터: 334,187개

### 3. 데이터 품질 조사 완료 (`src/explore_data.py`)
- description 채워진 비율: 페이지마다 60~100% 들쭉날쭉
- subjectKeyword/subjectCategory: 거의 0% (사용 불가)
- 발견: API의 description은 "보존상태 기록" 위주
  → RAG 자료로는 부적합

### 4. 큐레이터 추천 페이지 분석 완료
- URL: https://www.museum.go.kr/MUSEUM/contents/M0501000000.do
- 총 321건 (33페이지)
- 6개 카테고리: 선사·고대, 중·근세, 조각·공예, 서화, 아시아, 보존과학
- 작품 1개당 약 3,000자 깊이 있는 큐레이터 해설
- 큐레이터 실명 명시
- 라이선스: 공공누리 3유형 (출처표시+변경금지)
- **이게 K-Curator의 진짜 RAG 자료원**

## 데이터 소스 전략 (확정)

### 메인 RAG 자료
**큐레이터 추천 페이지 321건 (스크래핑)**
- URL 패턴 (리스트): `?cp={페이지}&searchId=recommend&relicRecommendUse=Y`
- URL 패턴 (상세): `?schM=view&relicRecommendId={ID}`
- 이미지 패턴: `https://www.museum.go.kr/files/zin/curator_{번호}_{n}.jpg`

### 메타데이터 보강
**e뮤지엄 API**
- 시대(temporal), 재질(medium) 등 안정적 메타데이터

### Phase 1 목표
**200점 → 321건 다 가져가도 무방**

## 지금까지 만든 스크립트

**`src/scrape_one.py`** — 작품 1건 스크래퍼. `scrape(relic_id)` / `save(data)` 함수 export.
**`src/scrape_list.py`** — 321건 ID/제목/썸네일 리스트 수집. 단일 요청(pageSize=500).
**`src/scrape_all.py`** — list 결과를 읽어 전수 수집. `--force` 옵션으로 재수집 가능.

추출 항목:
1. 제목 + 부제 + 큐레이터명 (`curator_NNN_tit.gif`의 alt 파싱; 콜론/대시 변형 처리)
2. 메타데이터 (작가, 시대, 재질, 크기, 소장번호, 등급) + `raw_caption` 원본 보존
3. 본문 (heading/paragraph/quote/caption 4종 블록, 순서 보존)
4. 이미지 URL + alt 캡션
5. 라이선스 텍스트

## Phase 1 데이터 수집 완료 상태 (2026-04-29)

전체 321건 → `data/raw/relic_{ID}.json` 저장 완료.

| 지표 | 값 |
|---|---|
| 총 작품 수 | 321 |
| 총 본문 글자 | 약 108만 자 |
| 평균 본문 길이 | 3,366자 |
| 총 본문 블록 | 4,497개 |
| 총 이미지 | 1,423장 |
| 큐레이터명 추출 성공 | 251/321 (78%) |

남은 빈 필드는 대부분 캡션에 원래 없는 정보(선사 유물엔 등급 없음 등).
필요 시 `raw_caption`에서 후처리 가능.

## 임베딩 / 벡터 DB (2026-04-29 완료)

**`src/build_index.py`** — 청킹 → 임베딩 → Chroma 인덱스 빌드
**`src/search.py`** — top-k 검색 (RAG 검증/디버그용)

- 청킹: heading 단위 섹션, 1500자 초과 시 paragraph 경계로 분할, 100자 미만 제거
- 모델: `intfloat/multilingual-e5-small` (passage:/query: 프리픽스, normalize_embeddings)
- 저장: `data/processed/chunks.jsonl` (사람용 덤프) + `data/chroma/` (kcurator_relics)

| 지표 | 값 |
|---|---|
| 청크 수 | 1,171 |
| 평균 길이 | 951자 (max 2,486 / min 110) |
| 임베딩 차원 | 384 (cosine) |
| Chroma 디스크 | ~24 MB |
| 빌드 시간 | 약 4분 (CPU) |

검색 스모크 테스트 결과 top-1 cosine 유사도 0.86~0.91 — 의미적 retrieval 작동 확인.
재빌드: `python src/build_index.py` (기존 컬렉션 자동 삭제 후 재생성)

## RAG 파이프라인 (2026-04-29 완료)

**`src/rag.py`** — 검색 → 컨텍스트 구성 → OpenAI 호출 → 스트리밍 출력
- 검색: build_index의 Chroma 컬렉션 재사용 (top-k 기본 5)
- LLM: `gpt-4o-mini`, temperature=0.7, system 프롬프트로 톤 분리
- 톤 모드 3종: `adult` (성인 존댓말) / `kid` (어린이 ~예요체) / `foreign` (영어, 한자 병기)
- 출처 자동 표기: `— 참고: <작품명> (큐레이터: 이름)` 등 모드별 포맷
- "자료에 없으면 모른다고 답하라" 가드레일 시스템 프롬프트에 포함

사용 예:
```
python src/rag.py "기영회도가 뭐야?" --mode kid
python src/rag.py "Tell me about the moon jar" --mode foreign
python src/rag.py "..." --no-stream --k 5
```

알려진 자잘한 이슈:
- foreign 모드에서 LLM이 출처를 가끔 `<자료 1>`로 카피해 적음 → 시스템 프롬프트 보강 필요

## 다음 단계 (우선순위)

1. ✅ `scrape_one.py` (1건 자동 수집)
2. ✅ `scrape_list.py` (321개 ID 리스트)
3. ✅ `scrape_all.py` (전체 수집 — 321/321 성공)
4. ✅ `build_index.py` + `search.py` (청킹/임베딩/Chroma)
5. ✅ `rag.py` (RAG, 어린이/성인/외국인 3-mode)
6. ⏳ Streamlit UI (작품 이미지 카드 + 톤 토글 + 멀티턴)

## 주의사항

- 스크래핑 시 서버 부담 줄이기: 요청 간 1~2초 sleep 권장
- 라이선스 표시 필수 (출처: 국립중앙박물관 / 공공누리 3유형)
- API 키 / 서비스키는 절대 GitHub에 커밋 X (`.env`는 `.gitignore` 등록 완료)
- 한국 정부 API/사이트는 가끔 한글 인코딩 이슈가 있을 수 있음
- 이미지는 멀티모달용으로 저작권 주의 (Phase 2)

## 코드 작성 가이드라인

- Python 3.13 기준
- 가상환경(.venv) 활성화 상태에서 작업
- 한글 주석/메시지 OK
- 함수는 짧고 명확하게
- 에러 처리는 명시적으로
- 출력 메시지에 이모지 자제 (Windows 콘솔 인코딩 이슈 방지)
- 데이터 저장은 항상 `data/raw/` (raw) 또는 `data/processed/` (정제)