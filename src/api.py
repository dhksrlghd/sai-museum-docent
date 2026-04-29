"""
K-Curator: FastAPI 백엔드
- POST /api/chat   — 검색 + LLM 스트리밍 (Server-Sent Events)
- GET  /api/works/{id} — 작품 상세 JSON (출처 카드 클릭 시 사용)
- GET  /api/health — 헬스체크

실행:
    uvicorn src.api:app --reload --port 8000
또는:
    python -m uvicorn src.api:app --reload --port 8000

CORS는 Vite dev (5173) 와 일반 5174 포트를 허용한다.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# 같은 디렉토리의 rag.py / build_index.py 재사용
from rag import (
    CHROMA_DIR,
    COLLECTION,
    EMBEDDING_MODEL,
    LLM_MODEL,
    QUERY_PREFIX,
    SYSTEM_PROMPTS,
    build_user_prompt,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
STATIC_DIR = PROJECT_ROOT / "frontend" / "dist"

load_dotenv(PROJECT_ROOT / ".env")

# ---- 전역 상태 (lifespan에서 1회 로드) ----
_state: dict = {
    "model": None,
    "collection": None,
    "thumbnails": {},  # relic_id -> list-card info
    "openai": None,
    "permanent": [],   # 상설전시 실 리스트
    "special": [],     # 특별전 리스트
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 무거운 초기화는 여기서 1회만
    from sentence_transformers import SentenceTransformer
    import chromadb
    from openai import OpenAI

    print("[api] Loading embedding model...")
    _state["model"] = SentenceTransformer(EMBEDDING_MODEL)

    print("[api] Connecting to Chroma...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    _state["collection"] = client.get_collection(COLLECTION)
    print(f"[api] Chroma collection '{COLLECTION}' size = {_state['collection'].count()}")

    list_path = RAW_DIR / "relic_list.json"
    if list_path.exists():
        data = json.loads(list_path.read_text(encoding="utf-8"))
        _state["thumbnails"] = {
            it["relic_recommend_id"]: it for it in data.get("items", [])
        }
        print(f"[api] Loaded {len(_state['thumbnails'])} thumbnail entries")

    perm_path = RAW_DIR / "permanent.json"
    if perm_path.exists():
        _state["permanent"] = json.loads(perm_path.read_text(encoding="utf-8")).get("rooms", [])
        print(f"[api] Loaded {len(_state['permanent'])} permanent rooms")

    sp_path = RAW_DIR / "special.json"
    if sp_path.exists():
        _state["special"] = json.loads(sp_path.read_text(encoding="utf-8")).get("exhibitions", [])
        print(f"[api] Loaded {len(_state['special'])} special exhibitions")

    if not os.getenv("OPENAI_API_KEY"):
        print("[api] WARNING: OPENAI_API_KEY not set — chat endpoint will fail")
    _state["openai"] = OpenAI()
    print("[api] Ready.")
    yield
    # shutdown: nothing to clean explicitly


app = FastAPI(title="K-Curator API", lifespan=lifespan)

# CORS: 환경변수로 추가 origin 등록 가능. 기본은 dev localhost.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174"
_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _default_origins).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 모델/스키마 ----
class ChatRequest(BaseModel):
    query: str
    mode: str = "adult"
    k: int = 5


# ---- 헬퍼 ----
def search_full(query: str, k: int) -> list[dict]:
    model = _state["model"]
    coll = _state["collection"]
    emb = model.encode([QUERY_PREFIX + query], normalize_embeddings=True)[0]
    res = coll.query(
        query_embeddings=[emb.tolist()],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        hits.append({"score": 1.0 - dist, "text": doc, "metadata": meta})
    return hits


def collect_sources(hits: list[dict]) -> list[dict]:
    """검색 결과 → 출처 카드 정보. 작품 단위로 dedupe."""
    seen: set = set()
    out: list[dict] = []
    for h in hits:
        meta = h["metadata"]
        rid = meta.get("relic_id")
        if rid in seen:
            continue
        seen.add(rid)
        thumb_info = _state["thumbnails"].get(rid, {})
        out.append(
            {
                "relic_id": rid,
                "title": meta.get("title", ""),
                "subtitle": meta.get("subtitle", ""),
                "curator": meta.get("curator", ""),
                "section": meta.get("section", ""),
                "period": meta.get("period", ""),
                "score": round(h["score"], 3),
                "thumbnail_url": thumb_info.get("thumbnail_url", ""),
                "detail_url": thumb_info.get("detail_url", meta.get("source_url", "")),
            }
        )
    return out


# ---- 엔드포인트 ----
@app.get("/api/health")
async def health() -> dict:
    coll = _state["collection"]
    return {
        "ok": True,
        "collection_size": coll.count() if coll else 0,
        "modes": list(SYSTEM_PROMPTS.keys()),
    }


@app.get("/api/works")
async def list_works(
    limit: int = 0, offset: int = 0, q: str = ""
) -> dict:
    """전체 작품 목록 (썸네일/제목/큐레이터). limit=0 이면 전체."""
    items = list(_state["thumbnails"].values())
    # 간단 검색: 제목에 q 포함
    if q:
        ql = q.lower()
        items = [it for it in items if ql in it.get("title_full", "").lower()]
    total = len(items)
    if limit:
        items = items[offset : offset + limit]
    return {"total": total, "offset": offset, "items": items}


@app.get("/api/exhibitions")
async def list_exhibitions() -> dict:
    """진행 중인 특별전/테마전 + 상설관 안내."""
    halls: list[dict] = []
    seen = set()
    for room in _state["permanent"]:
        h = room.get("hall", "")
        if h and h not in seen:
            seen.add(h)
            halls.append(
                {
                    "name": h,
                    "floor": room.get("floor", ""),
                    "rooms": [
                        {
                            "name": r.get("room_name", ""),
                            "showroom_code": r.get("showroom_code", ""),
                            "url": r.get("url", ""),
                            "works_count": len(r.get("works") or []),
                        }
                        for r in _state["permanent"]
                        if r.get("hall") == h
                    ],
                }
            )
    return {
        "halls": halls,
        "special": _state["special"],
    }


@app.get("/api/halls/{hall_name}")
async def get_hall(hall_name: str) -> dict:
    """특정 관의 상세 (실 리스트 + 각 실 작품 리스트)."""
    rooms = [r for r in _state["permanent"] if r.get("hall") == hall_name]
    if not rooms:
        raise HTTPException(404, f"hall '{hall_name}' not found")
    return {"hall": hall_name, "floor": rooms[0].get("floor", ""), "rooms": rooms}


@app.get("/api/works/{relic_id}")
async def get_work(relic_id: int) -> dict:
    fp = RAW_DIR / f"relic_{relic_id}.json"
    if not fp.exists():
        raise HTTPException(404, f"relic {relic_id} not found")
    data = json.loads(fp.read_text(encoding="utf-8"))
    # 리스트의 썸네일도 함께 끼워넣기 (있으면)
    thumb = _state["thumbnails"].get(relic_id, {})
    if thumb.get("thumbnail_url"):
        data["thumbnail_url"] = thumb["thumbnail_url"]
    return data


@app.post("/api/chat")
async def chat(req: ChatRequest):
    if req.mode not in SYSTEM_PROMPTS:
        raise HTTPException(400, f"invalid mode: {req.mode}")
    if not req.query.strip():
        raise HTTPException(400, "empty query")

    hits = search_full(req.query, req.k)
    sources = collect_sources(hits)

    user_prompt = build_user_prompt(req.query, hits)
    system_prompt = SYSTEM_PROMPTS[req.mode]
    client = _state["openai"]

    async def event_stream() -> AsyncIterator[dict]:
        # 1) 출처 카드 먼저
        yield {"event": "sources", "data": json.dumps(sources, ensure_ascii=False)}

        # 2) LLM 토큰 스트림 (OpenAI 동기 SDK 사용 — 토큰 단위로 yield)
        try:
            stream = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                stream=True,
            )
            for ev in stream:
                delta = ev.choices[0].delta.content
                if delta:
                    yield {"event": "token", "data": delta}
        except Exception as e:
            yield {"event": "error", "data": str(e)}
            return

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_stream())


# ---- 빌드된 React 정적 파일 서빙 (production) ----
# /api/* 라우트가 먼저 매칭되도록 순서가 중요. STATIC_DIR 존재 여부는
# 런타임에 매번 확인 (빌드가 컨테이너 시작 후에 끝날 수도 있음).
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(404)
    if not STATIC_DIR.exists():
        raise HTTPException(404, "frontend not built — run `npm run build`")
    target = STATIC_DIR / full_path
    if full_path and target.is_file():
        return FileResponse(target)
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(404, "index.html missing")
