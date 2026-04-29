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
- 설치된 라이브러리: requests, python-dotenv, beautifulsoup4, lxml
- API 키: `.env` 파일의 `EMUSEUM_API_KEY` (36자, KCISA 발급)

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

## 지금 작업 중인 것

**파일: `src/scrape_one.py`**

목표: 작품 1개(`<기영회도>` ID 2351292)를 자동 스크래핑해서 JSON으로 저장.

추출 항목:
1. 제목(메인+부제) + 큐레이터명
2. 메타데이터 캡션 (작가, 시대, 재질, 크기, 소장번호, 등급)
3. 본문 해설 (h5, p 태그 위주)
4. 이미지 URL 5장
5. 라이선스 정보

저장 위치: `data/raw/relic_{ID}.json`

테스트 작품 정보:
- 제목: 〈기영회도〉- 세 가지 복을 누린 원로 관료들의 잔치
- 큐레이터: 오다연
- 시대: 조선 1584년
- 재질: 비단에 색
- 등급: 보물 제1328호

## 다음 단계 (우선순위)

1. ✅ `scrape_one.py` 완성 + 테스트 (1개 작품 자동 수집)
2. ⏳ `scrape_list.py` (321개 작품 ID 리스트 수집)
3. ⏳ `scrape_all.py` (321개 전체 자동 스크래핑 → `data/raw/`)
4. ⏳ 텍스트 임베딩 + 벡터 DB 구축 (Chroma 또는 Qdrant)
5. ⏳ RAG 파이프라인 (어린이/성인 모드 시스템 프롬프트)
6. ⏳ Streamlit UI

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