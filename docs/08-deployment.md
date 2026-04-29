# 08. 배포 (Deployment)

## 한 줄 요약

**Hugging Face Spaces · Docker SDK 단일 컨테이너**.
프론트엔드(빌드된 React 정적 파일)와 백엔드(FastAPI/uvicorn)를 하나의 컨테이너가 같이 서빙합니다.

라이브 데모: [https://wangihong-k-curator.hf.space](https://wangihong-k-curator.hf.space)

## 왜 이 형태인가

| 옵션 | 장점 | 단점 |
|---|---|---|
| 한 컨테이너 (선택) | URL 하나, CORS 불필요, 단순 | cold start 약간 느림 |
| 분리 (Vercel + Render) | 프론트 글로벌 CDN | 두 곳 관리, CORS 설정 |
| Hugging Face Spaces | 무료 ML 친화적, git push 자동 | 다른 호스팅 대비 cold start |

ML 데모 + 무료 + 단순함의 균형으로 HF Spaces 선택.

## 인프라 한 그림

```
git push hf main
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  HF Space Builder                                    │
│   ├─ Stage 1: node:20-slim                           │
│   │     npm ci                                       │
│   │     npm run build  →  /app/frontend/dist         │
│   │                                                  │
│   ├─ Stage 2: python:3.12-slim                       │
│   │     apt-get install curl                         │
│   │     pip install torch (CPU index)                │
│   │     pip install -r requirements.txt              │
│   │     COPY src/, data/raw/, frontend/dist          │
│   │     RUN python src/build_index.py                │
│   │     RUN python src/embed_images.py               │
│   │                                                  │
│   └─ CMD: uvicorn api:app --host 0.0.0.0 --port 7860 │
└──────────────────────────────────────────────────────┘
       │
       ▼ Builder pushes image to HF
┌──────────────────────────────────────────────────────┐
│  HF Space Runtime  (CPU basic, 16GB RAM)             │
│   ├─ Container 1 replica                             │
│   ├─ stage = RUNNING_BUILDING → RUNNING              │
│   └─ Public URL: wangihong-k-curator.hf.space        │
└──────────────────────────────────────────────────────┘
```

## 디렉토리 구조 (배포 관점)

```
프로젝트 루트
├── .gitignore               .env, node_modules, .venv, data/chroma, .claude 제외
├── Dockerfile               2-stage: node + python
├── .dockerignore            git에 있어도 이미지에 안 들어갈 것들
├── requirements.txt         핀된 Python 의존성 (Pillow 포함)
├── README.md                HF Space 메타데이터 frontmatter (sdk: docker, app_port: 7860)
├── src/                     Python 백엔드 코드
├── frontend/
│   ├── package.json
│   ├── package-lock.json    npm ci에 필수
│   ├── vite.config.js
│   └── src/
└── data/
    └── raw/                 git에 포함 (RAG 소스)
```

## Dockerfile 핵심

```dockerfile
# ---- 1) Frontend build ----
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2) Python runtime ----
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/huggingface \
    PORT=7860

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# ⚠️ 중요: torch CPU 휠 먼저 — 안 그러면 4GB CUDA 다운로드
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/raw/ ./data/raw/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 인덱스를 이미지에 베이크 → cold start 단축
RUN python src/build_index.py
RUN python src/embed_images.py || echo "[warn] image embedding skipped"

RUN chmod -R 777 /app/.cache /app/data
EXPOSE 7860

CMD ["python", "-m", "uvicorn", "api:app", \
     "--app-dir", "src", \
     "--host", "0.0.0.0", \
     "--port", "7860"]
```

## HF Space 메타데이터 (README.md frontmatter)

```yaml
---
title: 사이 SAI · 한국 박물관 도슨트
emoji: 🏛️
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: 작품과 당신 사이 — 국립중앙박물관 큐레이터 해설 기반 RAG·멀티모달 도슨트
---
```

## 환경 변수 / 시크릿

HF Space 대시보드 → **Settings → Variables and secrets**:

| 키 | 필수? | 용도 |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | gpt-4o-mini 호출. 없으면 `/api/chat`, `/api/plan` 401 |
| `EMUSEUM_API_KEY` | 선택 | 데이터 재수집 시만. 빌드된 인덱스로 운영 시 불필요 |
| `CORS_ORIGINS` | 선택 | 추가 도메인 허용. 기본은 localhost |

`.env` 파일은 절대 커밋하지 않음 (`.gitignore`).

## 첫 배포 (5단계)

```bash
# 1. HF에서 New Space → Docker SDK → 이름 k-curator → Public

# 2. Space Settings → Variables and secrets → OPENAI_API_KEY 등록

# 3. 로컬 git 초기화
cd /path/to/project
git init
git add .
git commit -m "Initial release"
git branch -M main

# 4. HF remote + push
git remote add hf https://huggingface.co/spaces/<USERNAME>/k-curator
git push hf main
# username: HF 사용자명
# password: HF Write 토큰 (huggingface.co/settings/tokens 에서 발급)

# 5. https://huggingface.co/spaces/<USERNAME>/k-curator 의 Logs 탭에서 빌드 진행 확인
```

첫 빌드 약 **15~20분** (의존성 + 모델 + 894장 이미지 임베딩).
이후 push는 8~10분 (Docker layer cache 활용).

## 빌드 단계별 시간

```
0:00  builder 스폰
0:30  Stage 1 시작 (Node)
0:45  npm ci 완료
1:00  npm run build 완료 (Vite ~400ms)
1:30  Stage 2 시작 (Python)
2:00  apt curl 완료
3:00  torch CPU 휠 (190MB) 다운로드 완료
6:00  pip install -r requirements.txt 완료
6:30  src/, data/raw/, frontend/dist 복사
9:30  build_index.py (모델 다운 + 1265 청크 임베딩)
17:00 embed_images.py (894장 다운로드 + CLIP 임베딩)
17:30 chmod / 이미지 finalize
17:35 컨테이너 시작 + lifespan (모델 메모리 로드)
18:00 Application startup complete
18:15 RUNNING (App 탭 활성화)
```

## 운영 팁

### 빌드 실패 디버깅
- **Logs 탭 → Build** 에서 stage별 메시지 확인
- 가장 흔한 실패: `OPENAI_API_KEY` 미등록 시 챗 호출만 401 (빌드는 성공)
- pip 의존성 충돌: `requirements.txt` 핀 버전 검토

### Cold start 단축
- 모델·인덱스가 이미지에 베이크돼 있어 컨테이너 시작 후 약 30초면 ready
- 더 줄이고 싶으면 lifespan에서 `model.encode()` 한 번 워밍 호출 (현재 미적용)

### 새 데이터 반영
- 데이터만 갱신하고 싶으면 `data/raw/`만 변경 후 commit/push
- `Dockerfile RUN` 단계가 자동으로 `build_index.py` 재실행

### URL 변경
- HF Space는 한 번 만들어진 URL이 영구. rename 시 외부 공유 링크 깨짐
- 새 이름이 필요하면 새 Space를 만들어 push, 기존은 redirect 페이지로 처리

### 무료 티어 한계
- 14일 무사용 시 자동 sleep → 첫 진입 약 30초 wake up
- 16GB RAM 충분 (e5-small + CLIP + Chroma + uvicorn ≈ 2GB)
- 16GB 디스크 — 현재 이미지 약 3GB라 여유 있음

## 보안 체크리스트

- [x] `.env` 가 `.gitignore` 에 포함
- [x] `OPENAI_API_KEY` 가 HF Repository secret으로만 주입
- [x] 코드/커밋 메시지에 키 노출 없음
- [x] CORS는 명시 origin만 (현재 localhost dev + 미정 prod)
- [x] LLM 응답에 system prompt 노출 안 됨 (자료에 없는 내용 거부 가드레일 포함)
- [ ] Rate limit (현재 없음 — 트래픽 급증 시 OpenAI 비용 폭발 가능)
- [ ] WAF / DDoS 보호 (HF 기본 제공 수준)

## GitHub 으로의 이행 (선택)

HF Space는 git 저장소이지만 코드 공개·이슈 트래킹은 GitHub이 더 풍부합니다.
- GitHub 저장소 만들고 origin 추가:
  ```bash
  git remote add origin https://github.com/<USERNAME>/sai-museum-docent
  git push -u origin main
  ```
- HF에는 `git push hf main`, GitHub에는 `git push origin main` 으로 양쪽 갱신
- 또는 GitHub Actions로 push 시 HF에 mirror 가능
