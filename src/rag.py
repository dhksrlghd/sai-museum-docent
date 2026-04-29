"""
사이 (SAI): RAG 챗 파이프라인
- 검색: Chroma + e5-small (build_index.py와 동일 모델)
- 생성: OpenAI gpt-4o-mini
- 톤 모드: adult(성인) / kid(어린이) / foreign(외국인용 영어)

사용법:
    python src/rag.py "조선시대 잔치 그림을 보여줘"
    python src/rag.py "기영회도가 뭐야?" --mode kid
    python src/rag.py "Tell me about the moon jar" --mode foreign
    python src/rag.py "..." --k 5 --no-stream
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from build_index import (
    CHROMA_DIR,
    COLLECTION,
    EMBEDDING_MODEL,
    QUERY_PREFIX,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

LLM_MODEL = "gpt-4o-mini"
DEFAULT_K = 5

SYSTEM_PROMPTS = {
    "adult": (
        "당신은 '사이(SAI)' 라는 이름의 박물관 도슨트로, 작품과 관람객 사이를 잇습니다. "
        "국립중앙박물관 큐레이터의 해설만을 자료로 삼아 답변합니다. "
        "성인 일반 관람객 대상으로, 예의 있고 차분한 한국어 존댓말로 설명합니다. "
        "원전 큐레이터 해설을 충실히 인용하되, 자연스럽게 풀어쓰세요. "
        "답변 마지막에 '— 참고: <작품명> (큐레이터: 이름)' 형식으로 출처를 1~3개 표기하세요. "
        "제공된 자료에 없는 내용은 절대 지어내지 말고, 모르면 모른다고 답하세요."
    ),
    "kid": (
        "당신은 박물관에 처음 온 초등학생에게 작품을 설명해주는 친절한 도슨트 '사이'입니다. "
        "쉬운 단어, 짧은 문장, '~예요/~해요' 말투를 쓰세요. "
        "어려운 한자어는 풀어쓰고, 비유를 들어주세요(예: '아주 큰 항아리예요. 보름달처럼 둥글어요'). "
        "답변 마지막에 '— 알려준 사람: <작품명>의 큐레이터' 형식으로 출처를 표기하세요. "
        "자료에 없는 내용은 지어내지 말고, '그 부분은 잘 모르겠어요'라고 답하세요."
    ),
    "foreign": (
        "You are 'SAI' (사이, meaning 'in-between'), a museum docent that bridges visitors and Korean art. "
        "Answer in clear, natural English for an international visitor with no Korean background, "
        "grounded only in National Museum of Korea curators' commentary provided as context. "
        "Briefly transliterate or translate Korean terms when first introduced "
        "(e.g., 'Giyeonghoedo (耆英會圖, painting of an elders' gathering)'). "
        "End with '— Sources: <work title> (curator: name)' for 1-3 cited works. "
        "Never invent facts beyond the provided sources; say so if information is missing."
    ),
}


def search_full(query: str, k: int) -> list[dict]:
    """search.py와 비슷하지만 청크 전문(全文)을 함께 반환."""
    from sentence_transformers import SentenceTransformer
    import chromadb

    model = SentenceTransformer(EMBEDDING_MODEL)
    emb = model.encode([QUERY_PREFIX + query], normalize_embeddings=True)[0]
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    coll = client.get_collection(COLLECTION)
    res = coll.query(
        query_embeddings=[emb.tolist()],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {
            "score": 1.0 - dist,
            "text": doc,
            "metadata": meta,
        }
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        )
    ]


def format_context(hits: list[dict]) -> str:
    """검색 결과를 LLM 컨텍스트로 직렬화."""
    blocks = []
    for i, h in enumerate(hits, 1):
        meta = h["metadata"]
        title = meta.get("title", "")
        if meta.get("subtitle"):
            title = f"{title} - {meta['subtitle']}"
        curator = meta.get("curator") or "?"
        section = meta.get("section") or "(intro)"
        period = meta.get("period") or ""
        header = f"[자료 {i}] {title} / 섹션: {section} / 큐레이터: {curator}"
        if period:
            header += f" / 시대: {period}"
        blocks.append(f"{header}\n{h['text']}")
    return "\n\n---\n\n".join(blocks)


def build_user_prompt(query: str, hits: list[dict]) -> str:
    context = format_context(hits)
    return (
        "다음은 국립중앙박물관 큐레이터들이 작성한 작품 해설 자료입니다.\n"
        "이 자료만 참고해서 사용자의 질문에 답하세요.\n\n"
        f"=== 자료 시작 ===\n{context}\n=== 자료 끝 ===\n\n"
        f"[사용자 질문]\n{query}"
    )


def chat(query: str, mode: str, k: int, stream: bool) -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        print(
            "[rag] OPENAI_API_KEY가 .env에 없습니다. "
            "OPENAI_API_KEY=sk-... 한 줄을 추가해주세요.",
            file=sys.stderr,
        )
        sys.exit(2)

    from openai import OpenAI

    hits = search_full(query, k)
    print(f"[rag] retrieved {len(hits)}건  "
          f"(top score={hits[0]['score']:.3f}, "
          f"low={hits[-1]['score']:.3f})")
    for i, h in enumerate(hits, 1):
        meta = h["metadata"]
        print(f"   {i}. {meta.get('title','')[:35]:35s}  "
              f"sec={meta.get('section','')[:20]:20s}  "
              f"score={h['score']:.3f}")
    print()

    user_prompt = build_user_prompt(query, hits)
    system_prompt = SYSTEM_PROMPTS[mode]

    client = OpenAI()
    if stream:
        full = []
        s = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            stream=True,
        )
        for ev in s:
            delta = ev.choices[0].delta.content
            if delta:
                print(delta, end="", flush=True)
                full.append(delta)
        print()
        return "".join(full)
    else:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        text = resp.choices[0].message.content
        print(text)
        return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="질문 (한국어 또는 영어)")
    ap.add_argument(
        "--mode",
        choices=list(SYSTEM_PROMPTS.keys()),
        default="adult",
        help="톤 모드 (adult|kid|foreign)",
    )
    ap.add_argument("--k", type=int, default=DEFAULT_K, help="검색 top-k")
    ap.add_argument(
        "--no-stream", action="store_true", help="스트리밍 출력 끄기"
    )
    args = ap.parse_args()

    chat(args.query, args.mode, args.k, stream=not args.no_stream)
    return 0


if __name__ == "__main__":
    sys.exit(main())
