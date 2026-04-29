# =====================================================================
# K-Curator: 단일 컨테이너 배포 (Hugging Face Space, Docker SDK 호환)
#  - Stage 1: Node로 React/Vite 정적 빌드
#  - Stage 2: Python 슬림 런타임 + FastAPI(uvicorn)가 API + 정적파일 서빙
#  - 포트 7860은 HF Spaces 기본값
# =====================================================================

# ---- 1) Frontend build ----
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

# 의존성 캐싱
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# 소스 복사 후 build (vite → frontend/dist)
COPY frontend/ ./
RUN npm run build


# ---- 2) Python runtime ----
FROM python:3.12-slim

# Hugging Face Spaces는 비루트 유저(uid 1000)로 실행 → 권한 이슈 회피
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/huggingface \
    PORT=7860

WORKDIR /app

# 시스템 패키지 (lxml 빌드는 wheel이라 보통 불필요하나 안전하게)
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install -r requirements.txt

# 백엔드 코드 + 작품 JSON 321개 (RAG 소스)
COPY src/ ./src/
COPY data/raw/ ./data/raw/

# 빌드된 React를 컨테이너에 복사
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 임베딩 모델 다운로드 + Chroma 인덱스 빌드 (이미지에 베이크 → cold start 단축)
# 약 120MB e5-small 모델이 /tmp/hf_cache 에 캐시되고, data/chroma/ 가 생성된다.
RUN python src/build_index.py

# 캐시 디렉토리 권한 (HF Space는 비루트 1000 유저)
RUN chmod -R 777 /app/.cache /app/data

EXPOSE 7860

# uvicorn은 src/api.py 안의 app 객체를 띄움.
# --app-dir로 sys.path에 src 추가 (rag/build_index 모듈 임포트 위함).
CMD ["python", "-m", "uvicorn", "api:app", \
     "--app-dir", "src", \
     "--host", "0.0.0.0", \
     "--port", "7860"]
