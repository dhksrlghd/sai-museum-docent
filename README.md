---
title: K-Curator
emoji: 🏛️
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: 국립중앙박물관 큐레이터 추천 321점 RAG 도슨트 (어린이/성인/외국인 톤)
---

# K-Curator

국립중앙박물관 큐레이터들이 직접 작성한 추천 작품 **321점**의 해설을 RAG로 검색하고,
**OpenAI GPT-4o-mini**로 재작성해 어린이·성인·외국인 톤으로 답해주는 AI 도슨트입니다.

## 데모 화면

| 페이지 | 설명 |
|---|---|
| `/` | 다크 히어로 + 큐레이터 추천 12선 + AI 도슨트 CTA |
| `/browse` | 321점 갤러리 + 작품명 검색 |
| `/work/:id` | 큰 이미지 + 메타·본문 + sticky AI 패널 |
| `/ask` | 자유 챗 (3-mode 토글: 성인/어린이/Foreign) |

## 데이터 / 출처

모든 작품 텍스트·이미지는 [국립중앙박물관 큐레이터 추천 소장품](https://www.museum.go.kr/MUSEUM/contents/M0501000000.do)
페이지에서 스크래핑했고, **공공누리 3유형(출처표시+변경금지)** 라이선스를 따릅니다.

## 기술 스택

- **Frontend**: React 19 · React Router · Vite · Tailwind CSS v4
- **Backend**: FastAPI · uvicorn · sse-starlette (SSE 스트리밍)
- **검색**: Chroma (cosine, 1,171 chunk) · `intfloat/multilingual-e5-small` 임베딩
- **LLM**: OpenAI `gpt-4o-mini`
- **배포**: Hugging Face Space (Docker SDK)

## 로컬 실행

```powershell
# 1) Python venv 활성화 (.venv 가정)
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2) .env 작성
#   EMUSEUM_API_KEY=...   (스크래핑 단계만 필요)
#   OPENAI_API_KEY=sk-... (RAG 단계)

# 3) 데이터가 없다면 한 번 빌드 (약 13분)
python src/scrape_list.py
python src/scrape_all.py
python src/build_index.py

# 4) 백엔드
cd src
python -m uvicorn api:app --reload --port 8000

# 5) 프론트 (다른 터미널)
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## Hugging Face Space 배포

1. HF에서 New Space → Docker SDK → 이름 `k-curator`
2. Space의 **Settings → Repository secrets** 에 `OPENAI_API_KEY` 등록
3. 로컬에서 push:
   ```bash
   git remote add hf https://huggingface.co/spaces/<USER>/k-curator
   git push hf main
   ```
4. 빌드 완료(약 5~10분) 후 `https://<USER>-k-curator.hf.space` 에서 확인

> 첫 진입 시 sentence-transformers 모델(약 120MB)을 다운받기 때문에 cold start가 30초 정도 걸립니다.

## 디렉토리 구조

```
src/
  api.py              FastAPI 진입점 (API + SPA fallback)
  rag.py              검색 → 컨텍스트 구성 → LLM 호출
  build_index.py      청킹 + 임베딩 + Chroma 인덱스
  search.py           CLI 검색 도구 (디버그용)
  scrape_*.py         museum.go.kr 스크래퍼
frontend/
  src/pages/          Home, Browse, Work, Ask
  src/components/     Header, Footer, WorkCard, AskBox
  src/lib/api.js      백엔드 호출 + SSE 파서
data/
  raw/                작품별 JSON 321개 (사람이 읽을 수 있는 원본)
  chroma/             영구 벡터 인덱스 (24MB)
```
