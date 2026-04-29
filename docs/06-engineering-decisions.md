# 06. 엔지니어링 결정과 트레이드오프

기술 스택의 모든 선택에는 포기한 옵션이 있습니다. 이 문서는 **왜 그렇게 골랐고 무엇을 포기했는지**를 솔직히 정리한 회고입니다.

---

## 데이터 소스 — e뮤지엄 API vs 큐레이터 추천 페이지

**상황**: e뮤지엄 OpenAPI(KCISA)로 33만 건 메타데이터를 받을 수 있었음.

**시도한 것**: API의 `description` 필드를 RAG 자료로 쓰려고 1·중간·마지막 페이지 샘플링 (`src/explore_data.py`).

**발견**:
- description 채워진 비율 페이지마다 60~100% 들쭉날쭉
- 채워진 description도 대부분 "보존상태 기록" — *RAG 답변용으론 부적합*
- subjectKeyword/subjectCategory는 거의 0% (사용 불가)

**전환**: 박물관 사이트의 **큐레이터 추천 소장품** 섹션을 직접 스크래핑.
- 단 321건이지만 작품당 평균 3,400자의 깊이 있는 큐레이터 본문
- 큐레이터 실명·소속·전공이 명시
- 공공누리 3유형으로 재배포 가능

**교훈**:
> *데이터 양 < 데이터 품질.* 33만 건의 노이즈보다 321건의 잘 쓰인 본문이 훨씬 강력함. 첫 단계에서 데이터 품질 검증을 직접 해본 게 프로젝트 방향을 살림.

---

## 벡터 DB — Chroma vs 대안

**고려**: Chroma · Qdrant · Weaviate · pgvector · FAISS

**선택**: Chroma

**왜**:
- 파일 기반 (PersistentClient) → **단일 컨테이너 배포 단순**
- Python-native API, 학습 곡선 짧음
- 1,000~수만 청크 규모에 충분 (HNSW 내장)
- 메타데이터 필터 + cosine·L2 스페이스 지원

**포기한 것**:
- Qdrant의 더 풍부한 필터 표현식과 더 좋은 운영 도구
- pgvector의 SQL 통합
- 분산 인덱스 (수백만 청크 시 필요)

**평가**: 데이터 규모(1,265 청크, 733 이미지)에선 Chroma가 정확히 맞는 도구. 더 컸다면 Qdrant 선택했을 것.

---

## 임베딩 모델 — e5-small 선택의 이유

**고려**:
| 모델 | 차원 | 크기 | 한국어 |
|---|---|---|---|
| `intfloat/multilingual-e5-small` | 384 | 118MB | ✓ |
| `intfloat/multilingual-e5-base` | 768 | 280MB | ✓ |
| `BAAI/bge-m3` | 1024 | 2.2GB | ✓✓ |
| `jhgan/ko-sroberta-multitask` | 768 | 400MB | ✓ (Korean-specific) |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 118MB | △ |

**선택**: `e5-small`

**왜**:
- 무료 HF Space CPU 환경에서 모델 메모리 + 실행 속도 최적
- `passage:`/`query:` 프리픽스 대비 효과가 좋아 retrieval 품질 안정적
- 검증된 다국어 (50+ 언어), 한국어 retrieval top-1 cosine 0.86~0.91 측정
- 빌드 시 다운로드 ~3분 → 컨테이너 이미지 캐시되면 cold start 빠름

**포기한 것**:
- bge-m3의 더 높은 한국어 retrieval 품질 (KorBERT 계열 능가)
  - 무료 티어 디스크 한도, 빌드 시간 부담으로 보류
- 장기적으로는 v3에서 bge-m3 검토 (이슈 09-roadmap 참조)

---

## CLIP 모델 — multilingual의 함정

**처음 시도**: `clip-ViT-B-32-multilingual-v1` (한국어 텍스트→이미지 검색이 가능할 줄 알았음)

**발견**: 모델이 **텍스트 인코더만** 다국어로 갈아끼운 거라 이미지 인코딩 불가.
실행 시 `ValueError: Modality 'image' is not supported by this SentenceTransformer model. Supported modalities: text`

**해결**: 표준 `clip-ViT-B-32` (이미지+영어 텍스트)로 변경. 우리 핵심 use case(이미지→이미지 유사도)에는 충분.

**남은 한계**: 한국어 텍스트로 이미지 검색은 불가. 향후 두 모델을 같이 띄워(텍스트는 multilingual로, 이미지는 표준 CLIP으로) 해결 가능.

**교훈**:
> 모델 카드의 "modalities" 필드 미리 확인. 모델 이름이 multilingual이라고 모든 모달리티에 다국어가 적용되는 건 아님.

---

## LLM — gpt-4o-mini 선택

**고려**:
| 옵션 | 비용 | 한국어 | 셋업 |
|---|---|---|---|
| OpenAI gpt-4o-mini | 입력 $0.15 / 출력 $0.60 per 1M tok | 매우 좋음 | API 키 |
| Anthropic Claude | 비교 가능 | 매우 좋음 | API 키 |
| Google Gemini Flash | 무료 티어 | 좋음 | API 키 |
| Groq (Llama 70B) | 무료 티어 | 영어 위주 | API 키 |
| Ollama (qwen 7B 등) | 무료 (로컬) | 보통 | Docker 무거움 |

**선택**: gpt-4o-mini

**왜**:
- 사용자가 이미 결제해 둔 OpenAI 크레딧 활용
- 한국어 톤 변환(어린이/존댓말/영문) 품질 충분
- 호출당 ~$0.0008 — 1,000회 챗에 1달러 미만
- 스트리밍 안정성 검증됨

**포기한 것**:
- Anthropic Claude의 약간 더 자연스러운 한국어 (개인 의견)
- 무료 모델의 비용 제로

**LLM 추상화는 일부러 안 함**: 한 군데(api.py + rag.py)만 호출하므로 현재로썬 추상화 가치 < 복잡도. 모델 교체 필요 시 한 곳만 바꾸면 됨.

---

## 백엔드 — FastAPI vs Flask

**선택**: FastAPI

**왜**:
- async + SSE 자연스러움 (sse-starlette 통합)
- Pydantic BaseModel로 요청/응답 타입 안정성
- 자동 OpenAPI 문서 (`/docs`)
- uvicorn lifespan으로 모델·인덱스 1회 로드 깔끔하게 처리

**포기한 것**:
- Django의 ORM·admin (불필요)
- Flask의 더 가벼운 부트스트랩 (FastAPI도 충분히 가벼움)

---

## 프론트엔드 — React + Vite (Streamlit 안 쓴 이유)

**대안**:
- Streamlit: Python만으로 빠른 데모 가능
- Gradio: HF Space에선 거의 표준
- Next.js: 풀 React 프레임워크

**선택**: React + Vite + Tailwind

**왜**:
- "디자인 자유도가 높은 사이트"가 사용자 요구. Streamlit은 한계.
- HF Space Docker SDK로 React 빌드 정적 파일을 FastAPI가 함께 서빙 가능
- Vite 빌드 ~400ms 로 빠른 iteration
- 학습 가치(React/HTML/CSS) — 본인이 학습 중인 스택

**Next.js 안 쓴 이유**: 백엔드가 Python(FastAPI) 분리라 SSR 가치 없음. Vite SPA로 충분.

---

## 호스팅 — HF Spaces vs 분리 배포

**고려**:
- A. 한 컨테이너 통합 (Render/Fly.io 1개에 정적+API)
- B. 분리 배포 (Vercel = 정적, Render/Fly = 백엔드)
- C. **Hugging Face Spaces (Docker SDK)**

**선택**: C

**왜**:
- 사용자 익숙 (Hugging Face / Docker / RunPod 경험 있음)
- 무료 CPU (2 vCPU, 16GB RAM) — ML 모델 로드 충분
- 단일 git push로 자동 빌드+배포
- 도메인·SSL 자동
- ML 데모 친화적 (HF 커뮤니티에 노출)

**포기한 것**:
- 더 빠른 cold start (분리 배포가 쪼끔 빠름)
- 더 좋은 분석 도구

---

## Docker 빌드 — 이미지에 인덱스 베이크

**대안**:
- A. 컨테이너 시작 시 `build_index.py` 실행 (cold start 5분+)
- B. **Dockerfile RUN으로 빌드 시 미리 인덱스 생성** (이미지에 베이크)
- C. Chroma 인덱스를 git에 LFS로 포함

**선택**: B

**왜**:
- A는 cold start 마다 5분 — 사용자가 첫 진입에 503 받음
- C는 22MB+ binary가 git에 누적되면서 LFS 비용·운영 부담
- B는 빌드 시간(빌드 시 +7분)을 페이로드로 옮기고 cold start는 30초로 단축

**트레이드오프**:
- 빌드 시간 길어짐 (5분 → 12분)
- HF Space 무료 빌드 큐가 한 번에 한 개라 iteration 느려짐

---

## torch CPU-only

**문제**: 첫 HF 빌드에서 `pip install -r requirements.txt`가 nvidia_cuda_*, nvidia_cusolver-200MB, nvidia_cusparse-145MB 등 4GB+ CUDA 스택 다운로드 시작.

**원인**: 기본 PyPI 휠은 CUDA 포함. HF Space CPU 티어에선 무용지물.

**해결**:
```dockerfile
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
```

torch가 먼저 CPU 휠로 설치되면 sentence-transformers는 의존 만족된 걸 인식하고 그대로 사용. 4GB → 200MB로 절약.

**교훈**:
> ML 라이브러리 + 무료 호스팅 조합은 GPU 휠 자동 설치로 디스크/시간 폭발 가능. 명시적 CPU 휠 지정.

---

## SSE 스트리밍 — `\n\n` vs `\r\n\r\n`

**증상**: 프론트가 백엔드 응답을 받지만 토큰이 화면에 안 그려짐.

**원인**: 내가 처음 작성한 SSE 파서가 이벤트 구분자로 `\n\n`만 검색.
sse-starlette는 spec 표준대로 `\r\n\r\n` 송신. 내 파서는 영원히 매칭 못 함.

**해결**: 정규식 `\r\n\r\n|\n\n|\r\r`로 모든 EOL 변형 수용.

**교훈**:
> SSE는 표준이 있어도 라이브러리마다 구현이 다름. 파싱은 관대하게, 송신은 엄격하게 (Postel's Law).

---

## 디자인 — 한지 톤 + 단청 적색

**시도한 옵션**:
1. 미니멀 화이트 (Apple Museum-style)
2. 컬러풀 단청 (한국 전통 색채 풍부)
3. 한지 베이지 + 단청 적색 액센트 (선택)

**선택**: 옵션 3

**색 팔레트** (`@theme` in index.css):
```
--color-paper-50:  #faf8f3   (한지 따뜻한 크림)
--color-paper-100: #f3efe6   (살짝 어두운 크림)
--color-paper-200: #e6dfd0   (보더용)
--color-ink-500:   #6b6356   (보조 텍스트)
--color-ink-700:   #3d362b
--color-ink-900:   #15110a   (본문)
--color-vermilion-500: #a0301a   (단청 적색, 액센트)
--color-vermilion-600: #82261a
--color-vermilion-50:  #fbf2ef   (배지 배경)
```

**폰트**: 헤딩 Noto Serif KR, 본문 Noto Sans KR — 편집 디자인 톤.

**왜 이게 맞는가**:
- 박물관 = 차분, 고요, 무게감 → 화이트 한지 + 적색 점
- 단청 적색은 한국 전통 건축의 전면 색이라 정체성 직접 호응
- 텍스트 + 작품 이미지가 주연 → 배경은 캔버스 역할

---

## 청킹 사이즈 — 1500자 리미트

**근거**:
- e5-small max_seq_length: 512 tokens
- 한국어: 1자 ≈ 1.5~2 tokens → 1500자 ≈ 2,250~3,000 tokens
- 어… 그럼 초과네? **e5는 자동 truncation**, 정보 손실은 후반 발생

**그럼 왜 1500자?**
- 청크가 너무 짧으면 (예: 300자) 컨텍스트가 끊겨 retrieval 정확도 저하
- 너무 길면 (예: 5000자) 임베딩의 평균화 효과로 의미 흐려짐
- 1500자는 한국어 본문 1~2 단락 + 적당한 컨텍스트 포함

**예외**: 한 paragraph가 단독으로 1500자 초과면 자르지 않음 (의미 보존 우선).

**측정 결과**: max 2,486자 청크가 가끔 발생. truncation으로 후반 일부 손실되지만 시작이 의미 핵심이라 retrieval 품질엔 큰 영향 없음.

---

## 매칭 — 추천↔상설 fuzzy

**시도한 알고리즘**:
- A. 정확 일치만
- B. **정확 일치 OR substring (≥4자)** — 선택
- C. Levenshtein 편집거리 ≤ 2
- D. 임베딩 유사도

**왜 B**:
- A는 매칭률 너무 낮음 (제목 표기 다양 — `〈기영회도〉` vs `기영회도`)
- C는 false positive 위험 (전혀 다른 제목이 작은 편집거리 가질 수 있음)
- D는 의미는 같아도 표기 다른 작품을 잘 잡지만 무관한 작품도 잡힐 위험 + 처리 시간

**B의 결과**: 52/321 (16%) 매칭. 검수해보니 false positive 거의 없음 (안전한 보수적 매칭).

**한계**: 84%는 매칭 실패 — 이게 다 false negative라기보단 "큐레이터 추천했지만 현재 비전시"인 케이스가 다수.

---

## 결정 회고 — 한 줄 평가

| 결정 | 잘한가 | 메모 |
|---|---|---|
| 큐레이터 추천 페이지로 데이터 전환 | 매우 잘함 | 프로젝트 방향 자체를 살린 결정 |
| Chroma | 잘함 | 규모 대비 정확 |
| e5-small | 잘함 | 다국어 + 작은 사이즈 균형 |
| CLIP-B-32 | 보통 | 한국어 텍스트 검색 못 하는 한계, but 핵심 use case는 OK |
| FastAPI + React 분리 | 잘함 | 학습 + 디자인 자유도 둘 다 챙김 |
| HF Spaces | 매우 잘함 | 무료 + ML 친화적 + 단일 push 배포 |
| 매일 픽 cron-less | 잘함 | 단순한 결정적 회전이면 충분 |
| 멀티턴 대화 안 만듦 | 보통 | v3 후보로 미룸 |
