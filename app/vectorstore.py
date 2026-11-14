import logging
from functools import lru_cache
from pathlib import Path

import chromadb

from app.chunking import build_chunks
from app.embed import chunk_to_embed_text, embed_texts

CHROMA_DIR = Path(__file__).resolve().parent.parent / "data" / "chroma"
COLLECTION = "scholarsetu_chunks"


@lru_cache(maxsize=1)
def get_client():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def build_index():
    """(Re)build the collection from the downloaded pages. Returns the number of chunks."""
    chunks = build_chunks()
    if not chunks:
        raise RuntimeError("No chunks were made. Run: python -m app.fetch")
    client = get_client()
    try:
        client.delete_collection(COLLECTION)  # start clean so old chunks never linger
    except Exception:
        logging.info("No old collection to delete")
    collection = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embed_texts([chunk_to_embed_text(c) for c in chunks]),
        metadatas=[{"source": c["source"], "page": c["page"], "title": c["title"],
                    "chunk_index": c["chunk_index"]} for c in chunks],
    )
    logging.info("Indexed %s chunks in %s", len(chunks), CHROMA_DIR)
    return len(chunks)


def get_collection():
    """The collection; it is built first if it does not exist yet or is empty."""
    client = get_client()
    try:
        collection = client.get_collection(COLLECTION)
    except Exception:
        collection = None
    if collection is None or collection.count() == 0:
        build_index()
        collection = client.get_collection(COLLECTION)
    return collection


def search(query, top_k=5):
    """The best chunks for a query, each with score, title, source, page and text."""
    collection = get_collection()
    result = collection.query(
        query_embeddings=embed_texts([query]),
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for text, meta, distance in zip(result["documents"][0], result["metadatas"][0],
                                    result["distances"][0]):
        hits.append({
            "score": round(1 - distance, 4),  # cosine distance -> similarity
            "title": meta["title"],
            "source": meta["source"],
            "page": meta["page"],
            "chunk_index": meta["chunk_index"],
            "text": text,
        })
    return hits


if __name__ == "__main__":
    print(f"Indexed {build_index()} chunks")