import json
import logging
import re

from app.chunking import CHUNK_WORDS
from app.llm import ask_llm
from app.vectorstore import search

logger = logging.getLogger(__name__)

TOP_K = 3                    # how many chunks are given to the model
RAG_CHUNK_WORDS = CHUNK_WORDS  # chunk size used by /ask (change TOP_K and this to the evaluation winner)
MIN_RETRIEVAL_SCORE = 0.15   # below this the question is clearly unrelated: skip the model
MAX_SOURCE_CHARS = 1200      # each source is cut to this length in the prompt

IDK_TEXT = ("I don't know. I could not find this in the ScholarSetu sources. "
            "Please check the official portals: mahadbt.maharashtra.gov.in, "
            "scholarships.gov.in or dte.maharashtra.gov.in.")

SYSTEM_PROMPT = """You are ScholarSetu, an assistant for engineering students in Maharashtra, India. You answer questions about scholarships, fee concessions and hostel allowances.

You are given numbered SOURCES taken from official pages (DTE Maharashtra and the National Scholarship Portal). Rules:
1. Answer ONLY with facts that are written in the sources. Never use outside knowledge and never guess.
2. After each fact, add the number of the source it came from, like [1] or [2].
3. If the sources do not contain the answer, set "answerable" to false. This includes questions about something the sources do not mention, such as a college's own fees, a person, or a scheme that is not in the sources.
4. A scholarship or allowance amount is not a college fee. Do not answer a question about the hostel fee, admission fee or tuition fee of a college from a scholarship amount.
5. Use simple English and keep the answer short.
6. Do not state any amount, income limit or date that is not written in the sources.

Reply with JSON only, in exactly this shape:
{"answerable": true or false, "answer": "your answer with [n] markers, or an empty string if not answerable", "used_sources": [numbers of the sources you used], "confidence": "high, medium or low"}"""


def retrieve(question, top_k=TOP_K, chunk_words=RAG_CHUNK_WORDS):
    """The best chunks for the question (from the Chroma index)."""
    return search(question, top_k=top_k, chunk_words=chunk_words)


def build_user_message(question, chunks):
    parts = [f"Question: {question.strip()}", "", "Sources:"]
    for number, chunk in enumerate(chunks, start=1):
        text = chunk["text"][:MAX_SOURCE_CHARS]
        parts += [f"[{number}] {chunk['title']} (page {chunk['page']}) - {chunk['source']}", text, ""]
    return "\n".join(parts)


def parse_rag_reply(raw):
    """The model's JSON as a dict, or None if it is not usable."""
    text = raw.strip()
    try:
        data = json.loads(text[text.find("{"):text.rfind("}") + 1])
        answerable = data.get("answerable")
        if isinstance(answerable, str):
            answerable = answerable.strip().lower() == "true"
        confidence = str(data.get("confidence", "low")).strip().lower()
        if confidence not in ("high", "medium", "low"):
            confidence = "low"
        used = [int(n) for n in (data.get("used_sources") or []) if str(n).strip().isdigit()]
        return {"answerable": bool(answerable), "answer": str(data.get("answer", "")).strip(),
                "used_sources": used, "confidence": confidence}
    except (ValueError, TypeError, AttributeError):
        return None


def says_idk(text):
    """True if the answer text itself says it does not know."""
    return bool(re.match(r"\W*(i\s+(do\s+not|don['’]t)\s+know|i\s+(could\s+not|cannot|can['’]t)\s+find)",
                         text, re.IGNORECASE))


def summarise(chunks):
    """The retrieved chunks without their text (for the reply and for evaluation)."""
    return [{"n": i, "title": c["title"], "source": c["source"], "page": c["page"],
             "score": c["score"]} for i, c in enumerate(chunks, start=1)]


def dont_know(chunks):
    return {"answer": IDK_TEXT, "answerable": False, "confidence": "low",
            "citations": [], "retrieved": summarise(chunks)}


def answer_question(question, top_k=TOP_K, chunk_words=RAG_CHUNK_WORDS):
    """Answer from the retrieved chunks. Returns answer, answerable, confidence,
    citations (the sources the answer used) and retrieved (everything that was found)."""
    chunks = retrieve(question, top_k, chunk_words)
    if not chunks or chunks[0]["score"] < MIN_RETRIEVAL_SCORE:
        return dont_know(chunks)

    raw = ask_llm(SYSTEM_PROMPT, build_user_message(question, chunks),
                  temperature=0.0, max_tokens=1500, json_mode=True)
    reply = parse_rag_reply(raw)
    if reply is None:
        logger.warning("The model reply was not valid JSON; answering 'I don't know'")
        return dont_know(chunks)
    if not reply["answerable"] or not reply["answer"] or says_idk(reply["answer"]):
        return dont_know(chunks)

    cited = {n for n in reply["used_sources"] if 1 <= n <= len(chunks)}
    cited |= {int(n) for n in re.findall(r"\[(\d+)\]", reply["answer"]) if 1 <= int(n) <= len(chunks)}
    if not cited:  # no citation means no answer
        return dont_know(chunks)

    retrieved = summarise(chunks)
    return {
        "answer": reply["answer"],
        "answerable": True,
        "confidence": reply["confidence"],
        "citations": [item for item in retrieved if item["n"] in cited],
        "retrieved": retrieved,
    }