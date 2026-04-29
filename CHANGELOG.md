# Changelog

이 프로젝트의 모든 주목할 만한 변경 사항을 [Keep a Changelog](https://keepachangelog.com/) 형식으로 기록합니다.

---

## [v2.4] — 2026-04-30 — Rebrand: K-Curator → 사이 (SAI)

### Changed
- 브랜드명을 `K-Curator` 에서 `사이 (SAI)` 로 전면 교체
- 헤더 로고: letter-spacing 0.5em으로 글자 사이 빈 공간 강조 (이름 자체가 컨셉)
- 헤더 부제: "국립중앙박물관 큐레이터 추천 321선" → "작품과 당신 사이"
- 페이지 타이틀: "사이 · 한국 박물관 도슨트"
- 홈 히어로 카피: "큐레이터의 시선으로 보는 한국의 명품 321선" → "작품과 당신, / 그 사이를 잇다"
- LLM 시스템 프롬프트 3-mode 모두 `사이(SAI)` 자기소개로 변경
- 외국인 모드 자기소개에 "meaning in-between" 의미 설명 포함
- README, HF Space short_description, 푸터 등 노출 표기 일괄 변경

### Fixed
- 한국어 본문이 단어 중간에서 끊기는 줄바꿈 문제 — 모든 한국어 텍스트에 `break-keep` (word-break: keep-all) 적용

---

## [v2.3] — 2026-04-30 — Phase D · 마무리

### Added
- `match_locations.py` — 추천 321점 ↔ 상설 643점 fuzzy 매칭 (52점 매칭 성공)
- 추천 작품 메타에 hall/floor/room_name 부착 (코스 빌더 동선 정확도 ↑)
- 헤더 모바일 햄버거 메뉴 (md 미만)

### Changed
- `scrape_permanent.py` 파서 — 한국어 비율 필터로 alt 텍스트·반복 안내 제거
- 결과: 실 소개 텍스트 2,994자 → **23,314자 (8배 증가)**
- 작품 상세 우측 AskBox: 모바일에선 70vh 고정 높이로 stack
- README 전면 개정 (시나리오 표, 데이터 풍경, 25분 빌드 가이드)

### Fixed
- 검색 품질: "사유의 방" 쿼리가 이전엔 무관한 작품 잡았으나 이번엔 사유의 방 청크 직접 매칭

---

## [v2.2] — 2026-04-29 — 멀티모달 + 매일 큐레이션

### Added
- `embed_images.py` — 작품 이미지 CLIP 임베딩 (894장 시도, 733장 성공)
- 별도 Chroma 컬렉션 `kcurator_images` (cosine, 512-dim)
- API `GET /api/works/{id}/similar` — CLIP 이미지 유사도 닮은 작품 N점
- 작품 상세 하단 "이 작품과 닮은 작품" 6점 그리드 (유사도 % 표시)
- `daily_pick.py` — 30개 테마 풀, day-of-year 결정적 회전
- API `GET /api/today` — 오늘 테마 + 추천 6점 (당일 캐시)
- 홈 메인 섹션: 정적 추천 → 매일 바뀌는 큐레이션
- `requirements.txt`: Pillow 추가
- Dockerfile: build_index 후 embed_images 자동 실행

### Notes
- CLIP 모델 변경: `clip-multilingual-v1`(텍스트 전용) → 표준 `clip-ViT-B-32`(이미지+영어)
- 검증: 〈기영회도〉 → 호조낭관계회도 0.913, 문효세자 보양청계병 0.895 (CLIP이 의례 그림 클러스터링)

---

## [v2.1] — 2026-04-29 — 관람 코스 빌더

### Added
- `POST /api/plan` — SSE 스트리밍 코스 빌더 (시간/동반자/관심사 입력)
- 새 페이지 `/plan` — pill 토글 + 카드 + 자유 텍스트 입력 + 결과 마크다운 렌더링
- 후보 작품 썸네일 노출 (recommend는 작품 상세로 이동)
- 헤더에 '코스 짜기' 메뉴 추가

### Notes
- LLM이 후보 18점 중에서만 선별 — 자료 밖 작품 만들어내지 않도록 시스템 프롬프트 강제
- 동반자 톤 가이드 3종 (성인/어린이/외국인 영문)
- 출력 형식: 도입 단락 → ## H2 → ### 작품별 H3 → 화살표 이동 → 마무리

---

## [v2.0] — 2026-04-29 — 박물관 컴패니언 정체성

### Added
- `scrape_permanent.py` — 7관 39실 / 643점 작품 + 위치 메타 (1F/2F/3F)
- `scrape_special.py` — 진행중 특별·테마전 5건 + 본문 3,400자
- 통합 인덱스: 추천 + 상설 + 특별 → 1,171 → **1,223 청크**
- API `GET /api/exhibitions` — 7관 트리 + 진행중 특별전
- API `GET /api/halls/{name}` — 관별 실 + 작품 리스트
- 새 페이지 `/exhibitions` — 특별전 카드 + 층별 상설관 트리
- 헤더 4-tab 확장 (홈 / 전시 안내 / 소장품 / AI 도슨트)
- 홈 상단 "지금 박물관에서 · 특별전 N건 진행중" 띠

### Changed
- 정체성: "RAG 챗봇" → "박물관 컴패니언" (가기 전 / 가서 / 다녀와서)
- 챗 안에서 "지금 진행중인 특별전?" 같은 새 질문 답변 가능

### Fixed
- 특별전 카드 썸네일 깨짐 — hover 버튼 아이콘이 첫 `<img>`로 잡혀 onerror placeholder 표시되던 문제

---

## [v1.0] — 2026-04-29 — RAG 챗봇 데모

### Added
- 큐레이터 추천 321점 스크래핑 (`scrape_one`/`scrape_list`/`scrape_all`)
- 청킹 + e5-small 임베딩 + Chroma 인덱스 (1,171 청크)
- `rag.py` CLI 검색 도구
- FastAPI + SSE 스트리밍 (`/api/chat`)
- React/Vite 단일 챗 페이지 (3-mode 토글)
- 출처 카드 (썸네일 + 작품명 + 큐레이터)
- HF Space Docker SDK 단일 컨테이너 배포

### Notes
- 모델 선택: `intfloat/multilingual-e5-small` (118MB, 다국어, CPU 친화)
- LLM: OpenAI gpt-4o-mini (사용자 결제 환경 고려)
- 디자인: 한지 톤 + 단청 적색 + Noto Serif/Sans KR

### Fixed (early hotfix)
- SSE 파서 구분자: `\n\n` → `/\r\n\r\n|\n\n|\r\r/` (sse-starlette는 `\r\n\r\n` 송신)
- torch CPU 휠 명시 — 4GB CUDA 다운로드 회피
- `from rag import` 모듈 경로: `--app-dir src` 로 해결

---

## [v0.0] — 2026-04-29 — 데이터 탐색

### Decided
- 처음엔 e뮤지엄 OpenAPI(KCISA)로 33만 건 메타데이터 활용 시도
- 발견: API의 `description`이 "보존상태 기록" 위주 — RAG 자료로 부적합
- 전환: 박물관 사이트의 큐레이터 추천 321건을 직접 스크래핑하기로
