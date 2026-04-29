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
from daily_pick import today_theme, picks_for_theme

IMAGE_COLLECTION = "kcurator_images"
CLIP_MODEL_NAME = "sentence-transformers/clip-ViT-B-32"

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
    "clip_model": None,
    "image_collection": None,
    "today_cache": {},  # date_str -> {theme, picks}
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

    # CLIP 이미지 컬렉션 (있으면 로드)
    try:
        _state["image_collection"] = client.get_collection(IMAGE_COLLECTION)
        print(f"[api] Image collection size = {_state['image_collection'].count()}")
        # 이미지 컬렉션이 있으면 CLIP 이미지 인코더 모델도 로드
        print(f"[api] Loading CLIP model: {CLIP_MODEL_NAME}")
        _state["clip_model"] = SentenceTransformer(CLIP_MODEL_NAME)
        print("[api] CLIP model ready.")
    except Exception as e:
        print(f"[api] No image collection ({e}); /similar endpoint disabled.")

    print("[api] Ready.")
    yield
    # shutdown: nothing to clean explicitly


app = FastAPI(title="사이 (SAI) API", lifespan=lifespan)

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


class PlanRequest(BaseModel):
    duration_min: int = 60        # 30/60/90/120
    companion: str = "self"       # self | kid | foreign
    interests: str = ""           # 자유 텍스트
    k: int = 18                   # 후보 작품 retrieval 개수


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


@app.get("/api/today")
async def today_pick() -> dict:
    """오늘의 테마 + 추천 작품 6점 (당일 캐시)."""
    import datetime as _dt
    today = _dt.date.today()
    key = today.isoformat()
    cached = _state["today_cache"].get(key)
    if cached:
        return cached
    theme = today_theme(today)
    picks = picks_for_theme(
        theme,
        _state["model"],
        _state["collection"],
        _state["thumbnails"],
        QUERY_PREFIX,
        n=6,
    )
    out = {"date": key, "theme": theme, "picks": picks}
    _state["today_cache"][key] = out
    # 어제 캐시는 자동 청소
    for k in list(_state["today_cache"].keys()):
        if k != key:
            _state["today_cache"].pop(k, None)
    return out


@app.get("/api/works/{relic_id}/similar")
async def similar_works(relic_id: int, k: int = 6) -> dict:
    """이미지 임베딩으로 유사 작품 N점.
    해당 작품의 첫 이미지 임베딩을 query로 사용한다.
    """
    img_coll = _state.get("image_collection")
    if not img_coll:
        raise HTTPException(503, "image index not available")

    # 1) 입력 작품의 임베딩 ID 후보들
    src = img_coll.get(
        where={"relic_id": relic_id},
        include=["embeddings", "metadatas"],
    )
    if not src["ids"]:
        raise HTTPException(404, f"no images indexed for relic {relic_id}")

    # 2) 첫 이미지의 임베딩으로 유사 검색
    query_emb = src["embeddings"][0]
    res = img_coll.query(
        query_embeddings=[query_emb if isinstance(query_emb, list) else query_emb.tolist()],
        n_results=k * 4 + 1,  # 자기 자신 + 같은 작품 dedupe 여유
        include=["metadatas", "distances"],
    )

    # 3) 같은 작품 제외 + 작품 단위 dedupe
    seen: set = {relic_id}
    out: list[dict] = []
    for meta, dist in zip(res["metadatas"][0], res["distances"][0]):
        rid = meta.get("relic_id")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        thumb = _state["thumbnails"].get(rid, {})
        out.append(
            {
                "relic_id": rid,
                "title": meta.get("title", ""),
                "subtitle": meta.get("subtitle", ""),
                "curator": meta.get("curator", ""),
                "period": meta.get("period", ""),
                "image_url": meta.get("url", ""),
                "thumbnail_url": thumb.get("thumbnail_url", "") or meta.get("url", ""),
                "score": round(1.0 - dist, 3),
            }
        )
        if len(out) >= k:
            break
    return {"source_relic_id": relic_id, "similar": out}


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


# ---- 관람 코스 빌더 ----
COMPANION_HINT = {
    "self": "성인 1인 관람.  차분한 큐레이터 톤으로 작품의 핵심 가치를 짚어 주세요.",
    "kid":  "어린이 동반.  '~예요/~해요' 말투, 시각적이고 흥미로운 작품 위주로, 어려운 한자어는 피하세요.",
    "foreign": "외국인 동반.  반드시 영어로 작성하되 작품명은 한자/한글 병기 (예: Banga Sayusang 半跏思惟像 / 'Pensive Bodhisattva'). 한국 문화 입문에 좋은 대표작 위주.",
}

PLAN_SYSTEM_PROMPT = (
    "You are a National Museum of Korea tour-curating expert. "
    "Given visitor constraints and a list of candidate works (with their gallery locations), "
    "design an efficient, narrative-driven viewing course. "
    "Strictly use only the works in the candidate list — never invent works. "
    "Optimize the path so that gallery-floor transitions are minimized "
    "(group works by floor, then by hall, in order 1F → 2F → 3F or reverse). "
    "Allocate roughly 6–10 minutes per work plus 3 minutes between floors. "
    "If the candidate list does not contain enough on-display works, "
    "you may still include curator-recommended works (without specific location) "
    "and clearly mark them as '큐레이터 추천 (위치 정보 없음)'."
)


def plan_user_prompt(req: PlanRequest, candidates: list[dict]) -> str:
    cand_lines = []
    for i, c in enumerate(candidates, 1):
        meta = c["metadata"]
        title = meta.get("title", "")
        sub = meta.get("subtitle", "")
        full = f"{title} - {sub}" if sub else title
        cat = meta.get("category", "")
        loc = meta.get("location", "") or (
            f"{meta.get('hall','')} {meta.get('floor','')}" if meta.get("hall") else "위치 정보 없음"
        )
        period = meta.get("period", "")
        snippet = c["text"][:180].replace("\n", " ")
        cand_lines.append(
            f"[{i}] ({cat}) {full}\n"
            f"    위치: {loc}  / 시대: {period}\n"
            f"    요약: {snippet}…"
        )
    cand_block = "\n".join(cand_lines)

    companion_label = {"self": "성인 1인", "kid": "어린이와 함께", "foreign": "외국인 친구와 함께"}[req.companion]

    return (
        f"=== 관람객 정보 ===\n"
        f"가용 시간: {req.duration_min}분\n"
        f"동반자: {companion_label}\n"
        f"동반자 톤 가이드: {COMPANION_HINT[req.companion]}\n"
        f"관심사: {req.interests or '(미지정 — 박물관 대표작 중심)'}\n\n"
        f"=== 작품 후보 ({len(candidates)}점) ===\n"
        f"{cand_block}\n\n"
        f"위 후보에서 가용 시간에 맞게 4~7점을 골라 코스를 작성하세요.\n\n"
        f"출력 형식 (한국어 마크다운, 단 동반자가 외국인이면 영어로):\n"
        f"## 오늘의 코스 — 약 {req.duration_min}분\n\n"
        f"한 단락 도입 (3~4줄): 오늘 코스의 테마와 동선 한 줄 요약.\n\n"
        f"### 1. 작품명 — 위치 (X분)\n"
        f"왜 이 작품을 골랐는지, 무엇을 주목해서 볼지 2~3문장.\n\n"
        f"### 2. 작품명 — 위치 (X분)\n"
        f"...\n\n"
        f"각 작품 사이에 층/관 이동이 있으면 화살표 한 줄로 표시: \n"
        f"`→ 1F 선사·고대관 → 2F 서화관 (이동 3분)`\n\n"
        f"마지막에 한 단락 마무리 인사."
    )


def fetch_plan_candidates(req: PlanRequest) -> list[dict]:
    """관심사 임베딩으로 top-k 청크 retrieve, 작품 단위 dedupe."""
    model = _state["model"]
    coll = _state["collection"]
    seed = req.interests.strip() or "한국 미술 대표작"
    emb = model.encode([QUERY_PREFIX + seed], normalize_embeddings=True)[0]
    res = coll.query(
        query_embeddings=[emb.tolist()],
        n_results=req.k * 3,  # dedupe 위해 넉넉히
        include=["documents", "metadatas", "distances"],
    )
    out: list[dict] = []
    seen = set()
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        key = meta.get("relic_id") or (meta.get("title", ""), meta.get("category", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": doc, "metadata": meta, "score": 1.0 - dist})
        if len(out) >= req.k:
            break
    return out


@app.post("/api/plan")
async def plan(req: PlanRequest):
    if req.companion not in COMPANION_HINT:
        raise HTTPException(400, f"invalid companion: {req.companion}")
    if req.duration_min not in (30, 60, 90, 120, 180):
        raise HTTPException(400, "duration_min must be one of 30/60/90/120/180")

    candidates = fetch_plan_candidates(req)
    course_meta = [
        {
            "relic_id": c["metadata"].get("relic_id"),
            "title": c["metadata"].get("title", ""),
            "subtitle": c["metadata"].get("subtitle", ""),
            "category": c["metadata"].get("category", ""),
            "hall": c["metadata"].get("hall", ""),
            "floor": c["metadata"].get("floor", ""),
            "location": c["metadata"].get("location", ""),
            "thumbnail_url": _state["thumbnails"].get(
                c["metadata"].get("relic_id"), {}
            ).get("thumbnail_url", "")
            or c["metadata"].get("thumbnail_url", ""),
        }
        for c in candidates
    ]

    user_prompt = plan_user_prompt(req, candidates)
    client = _state["openai"]

    async def event_stream() -> AsyncIterator[dict]:
        yield {
            "event": "candidates",
            "data": json.dumps(course_meta, ensure_ascii=False),
        }
        try:
            stream = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": PLAN_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.6,
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
