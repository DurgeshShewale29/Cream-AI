import logging
from functools import lru_cache
from pathlib import Path

import chromadb

from app.chunking import CHUNK_WORDS, build_chunks, overlap_for
from app.embed import chunk_to_embed_text, embed_texts

CHROMA_DIR = Path(__file__).resolve().parent.parent / "data" / "chroma"
COLLECTION = "scholarsetu_chunks"
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_client():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def collection_name(chunk_words=CHUNK_WORDS):
    """The normal chunk size keeps the Day 7 name; other sizes get their own collection."""
    return COLLECTION if chunk_words == CHUNK_WORDS else f"{COLLECTION}_{chunk_words}"


def build_index(chunk_words=CHUNK_WORDS):
    """(Re)build the collection from the downloaded pages. Returns the number of chunks."""
    chunks = build_chunks(size=chunk_words, overlap=overlap_for(chunk_words))
    if not chunks:
        raise RuntimeError("No chunks were made. Run: python -m app.fetch")
    client = get_client()
    name = collection_name(chunk_words)
    try:
        client.delete_collection(name)  # start clean so old chunks never linger
    except (chromadb.errors.ChromaError, ValueError):
        logger.info("No old collection to delete")
    collection = client.create_collection(name, metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embed_texts([chunk_to_embed_text(c) for c in chunks]),
        metadatas=[{"source": c["source"], "page": c["page"], "title": c["title"],
                    "chunk_index": c["chunk_index"]} for c in chunks],
    )
    logger.info("Indexed %s chunks (%s words each) in %s", len(chunks), chunk_words, CHROMA_DIR)
    return len(chunks)


def get_collection(chunk_words=CHUNK_WORDS):
    """The collection; it is built first if it does not exist yet or is empty."""
    client = get_client()
    name = collection_name(chunk_words)
    try:
        collection = client.get_collection(name)
    except (chromadb.errors.ChromaError, ValueError):
        collection = None
    if collection is None or collection.count() == 0:
        build_index(chunk_words)
        collection = client.get_collection(name)
    return collection


def search(query, top_k=5, chunk_words=CHUNK_WORDS):
    """The best chunks for a query, each with score, title, source, page and text."""
    collection = get_collection(chunk_words)
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