import logging
import os
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

from app.chunking import CHUNK_WORDS, OVERLAP_WORDS, build_chunks

load_dotenv()

MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
MIN_SCORE = 0.30  # a best score below this is reported as "no confident match"
TOP_K = 3

BASE_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_FILE = BASE_DIR / "docs" / "how_llms_work.md"
OUT_FILE = BASE_DIR / "eval" / "search_results.md"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class EmbeddingError(RuntimeError):
    """The embedding model could not be loaded or used."""


@lru_cache(maxsize=1)
def get_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise EmbeddingError("sentence-transformers is not installed. Run: pip install -r requirements.txt")
    try:
        return SentenceTransformer(MODEL_NAME)
    except Exception as error:
        raise EmbeddingError(f"Could not load the embedding model '{MODEL_NAME}' "
                             f"(it needs internet the first time): {error}")


def embed_texts(texts):
    """Text -> list of vectors (each vector is a list of numbers, length 1 = normalised)."""
    vectors = get_model().encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vectors, dtype=float).tolist()


def chunk_to_embed_text(chunk):
    """The text that is embedded: the title helps the search find the right scheme."""
    return f"{chunk['title']}. {chunk['text']}"


def semantic_search(query, chunks, matrix, top_k=TOP_K):
    """Best `top_k` chunks for a query, as (chunk, score). The score is cosine similarity."""
    query_vector = np.asarray(embed_texts([query])[0], dtype=float)
    scores = matrix @ query_vector
    best = np.argsort(-scores)[:top_k]
    return [(chunks[i], float(scores[i])) for i in best]


def load_questions():
    """The numbered questions under '## ScholarSetu user questions' in the notes file."""
    text = QUESTIONS_FILE.read_text(encoding="utf-8")
    section = text.split("## ScholarSetu user questions")[-1]
    questions = []
    for line in section.splitlines():
        match = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if match:
            questions.append(re.sub(r"\s*\*\(.*\)\*\s*$", "", match.group(1)).strip())
    return questions


def one_line(text, limit=150):
    text = " ".join(text.split()).replace("|", "/")
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def write_results(questions, results, chunks):
    sources = len({c["source"] for c in chunks})
    lines = [
        "# Semantic search results",
        "",
        f"Run on {date.today().isoformat()} with `{MODEL_NAME}`. {len(chunks)} chunks from "
        f"{sources} source pages (about {CHUNK_WORDS} words per chunk, {OVERLAP_WORDS} words overlap). "
        "Every chunk keeps its source, page and title.",
        "",
        "Each question is turned into an embedding and compared with every chunk by cosine "
        f"similarity. The top {TOP_K} hits are listed. A best score below {MIN_SCORE} is marked "
        '"no confident match".',
        "",
        "## Summary",
        "| # | Question | Best hit | Score | Result |",
        "|---|---|---|---|---|",
    ]
    weak = []
    for number, (question, hits) in enumerate(zip(questions, results), start=1):
        chunk, score = hits[0]
        found = score >= MIN_SCORE
        if not found:
            weak.append(f"Q{number}")
        lines.append(f"| {number} | {one_line(question, 90)} | {one_line(chunk['title'], 70)} | "
                     f"{score:.2f} | {'found' if found else 'no confident match'} |")
    lines += ["", ("Questions with no confident match: " + ", ".join(weak) + "." if weak
                   else "Every question had a confident match."), "", "## Hits per question"]
    for number, (question, hits) in enumerate(zip(questions, results), start=1):
        lines += ["", f"### Q{number}. {question}", "",
                  "| Rank | Score | Title | Source | Page | Chunk starts with |",
                  "|---|---|---|---|---|---|"]
        for rank, (chunk, score) in enumerate(hits, start=1):
            lines.append(f"| {rank} | {score:.2f} | {one_line(chunk['title'], 70)} | {chunk['source']} | "
                         f"{chunk['page']} | {one_line(chunk['text'])} |")
    OUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    questions = load_questions()
    if not questions:
        raise SystemExit("No questions found in docs/how_llms_work.md")
    chunks = build_chunks()
    if not chunks:
        raise SystemExit("No chunks were made. Run: python -m app.fetch")
    try:
        matrix = np.asarray(embed_texts([chunk_to_embed_text(c) for c in chunks]), dtype=float)
        results = [semantic_search(q, chunks, matrix) for q in questions]
    except EmbeddingError as error:
        raise SystemExit(f"{error}\nNothing was written.")
    write_results(questions, results, chunks)
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()