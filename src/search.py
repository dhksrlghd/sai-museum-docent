"""
K-Curator: Chroma 인덱스 검색 (RAG 검증용)
사용법:
    python src/search.py "조선시대 잔치 그림"
    python src/search.py "조선시대 잔치 그림" --k 10
"""

import argparse
import sys
from pathlib import Path

from build_index import (
    CHROMA_DIR,
    COLLECTION,
    EMBEDDING_MODEL,
    QUERY_PREFIX,
)


def search(query: str, k: int = 5) -> list[dict]:
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

    hits = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        hits.append(
            {
                "score": 1.0 - dist,  # cosine distance → similarity
                "title": meta.get("title", ""),
                "subtitle": meta.get("subtitle", ""),
                "section": meta.get("section", ""),
                "curator": meta.get("curator", ""),
                "snippet": doc[:200].replace("\n", " "),
            }
        )
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="검색 쿼리 (한국어)")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    hits = search(args.query, args.k)
    print(f"[search] '{args.query}' top-{args.k}:")
    print("=" * 70)
    for i, h in enumerate(hits, 1):
        title = h["title"]
        if h["subtitle"]:
            title = f"{title} - {h['subtitle']}"
        section = f" / [{h['section']}]" if h["section"] else ""
        print(
            f"[{i}] score={h['score']:.3f}  {title}{section}"
            f"  ({h['curator'] or '큐레이터?'})"
        )
        print(f"    {h['snippet']}...")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
