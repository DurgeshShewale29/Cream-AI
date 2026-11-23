import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.cache import query_cache
from app.llm import LLMError, ask_llm, get_last_usage
from app.records import get_by_id, load_records
from app.security import validate_input
from app.smart_search import smart_search
from app.stacking import analyze_stacking, filter_eligible_records

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_JSON = BASE_DIR / "data" / "questions.json"
FEEDBACK_JSON = BASE_DIR / "data" / "feedback.json"
PROMPTS_DIR = BASE_DIR / "prompts"

app = FastAPI(
    title="ScholarSetu API",
    description="Scholarship schemes for Maharashtra engineering students (DTE Maharashtra + NSP).",
    version="0.1.0",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log request latency and token metrics, and set telemetry headers."""
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"

    usage = get_last_usage()
    if usage.get("total_tokens", 0) > 0:
        response.headers["X-Total-Tokens"] = str(usage["total_tokens"])

    logger.info(
        "Request method=%s path=%s status=%d latency_ms=%.2f prompt_tokens=%d completion_tokens=%d total_tokens=%d",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
        usage.get("total_tokens", 0),
    )
    return response


class Scheme(BaseModel):
    id: int
    scheme_name: str
    department: str
    eligible_category: str
    income_limit: int | None = None
    benefit: str
    source_url: str
    verified: bool = False


class ScoredScheme(Scheme):
    score: float


class SearchResult(BaseModel):
    query: str
    count: int
    results: list[ScoredScheme]


class SemanticHit(BaseModel):
    score: float
    title: str
    source: str
    page: int
    chunk_index: int
    text: str


class SemanticResult(BaseModel):
    query: str
    count: int
    results: list[SemanticHit]


class QuestionIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    name: str | None = Field(default=None, max_length=100)


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    prompt_version: Literal["v1", "v2"] = "v2"


class ChatOut(BaseModel):
    answer: str
    confidence: Literal["high", "medium", "low"]
    follow_up: str


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class Citation(BaseModel):
    n: int
    title: str
    source: str
    page: int
    score: float


class AskOut(BaseModel):
    question: str
    answer: str
    answerable: bool
    confidence: Literal["high", "medium", "low"]
    citations: list[Citation]


class AgentIn(BaseModel):
    question: str | None = Field(default=None, min_length=3, max_length=500)
    thread_id: str | None = Field(default=None, min_length=1, max_length=100)
    approve: bool | None = None


class AgentStep(BaseModel):
    action: str
    input: Any
    observation: str


class AgentOut(BaseModel):
    thread_id: str
    status: Literal["answered", "awaiting_approval"]
    answer: str | None = None
    pending_action: dict | None = None
    steps: list[AgentStep]
    tools_used: list[str]
    turns: int


class QuestionSaved(BaseModel):
    id: int
    question: str
    name: str | None = None
    created_at: str


class FeedbackIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=5000)
    endpoint: Literal["/ask", "/agent"]
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=500)
    citations_count: int = Field(default=0, ge=0)
    thread_id: str | None = Field(default=None, max_length=100)


class FeedbackSaved(FeedbackIn):
    id: int
    created_at: str


class FeedbackSummary(BaseModel):
    total: int
    up: int
    down: int
    items: list[FeedbackSaved]


class StackingIn(BaseModel):
    scheme_ids: list[int] | None = None
    category: str = "EWS"
    gender: Literal["Female", "Male"] = "Female"
    family_income: int | None = Field(default=400_000, ge=0)
    annual_fee: int = Field(default=100_000, ge=0, le=5_000_000)
    has_disability: bool = False
    is_hosteller: bool = True
    city_tier: Literal["metro", "non_metro"] = "metro"
    include_abroad: bool = False


class CacheStatsOut(BaseModel):
    size: int
    max_size: int
    hits: int
    misses: int
    hit_ratio: float


def read_questions():
    """Return the saved questions (empty list if the file is missing or broken)."""
    try:
        with open(QUESTIONS_JSON, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_question(question, name=None):
    """Append one question to data/questions.json and return the saved entry."""
    questions = read_questions()
    entry = {
        "id": len(questions) + 1,
        "question": question.strip(),
        "name": name.strip() if name else None,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    questions.append(entry)
    with open(QUESTIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    return entry


def read_feedback():
    """Return saved thumbs up/down entries (empty list if the file is missing or broken)."""
    try:
        with open(FEEDBACK_JSON, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_feedback(body: FeedbackIn):
    """Append one thumbs up/down entry to data/feedback.json and return it."""
    items = read_feedback()
    entry = {
        "id": len(items) + 1,
        "question": body.question.strip(),
        "answer": body.answer.strip(),
        "endpoint": body.endpoint,
        "rating": body.rating,
        "comment": body.comment.strip() if body.comment else None,
        "citations_count": body.citations_count,
        "thread_id": body.thread_id,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    items.append(entry)
    FEEDBACK_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    return entry


def load_prompt(filename):
    """Read one prompt file from the prompts/ folder."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


def parse_chat_reply(raw):
    """Turn the model's text into (answer, confidence, follow_up). The flag says if it was valid JSON."""
    text = raw.strip()
    try:
        data = json.loads(text[text.find("{"):text.rfind("}") + 1])
        answer = str(data["answer"]).strip()
        if not answer:
            raise ValueError("empty answer")
        confidence = str(data.get("confidence", "low")).strip().lower()
        if confidence not in ("high", "medium", "low"):
            confidence = "low"
        follow_up = str(data.get("follow_up") or "").strip()
        return {"answer": answer, "confidence": confidence, "follow_up": follow_up}, True
    except (ValueError, KeyError, TypeError):
        return {"answer": text[:1000], "confidence": "low", "follow_up": ""}, False


def answer_question(question, version="v2"):
    """Ask the model one question using the system prompt and a task prompt version."""
    system_prompt = load_prompt("system.txt")
    task_prompt = load_prompt(f"task_{version}.txt").replace("{question}", question.strip())
    raw = ask_llm(system_prompt, task_prompt, json_mode=True)
    return parse_chat_reply(raw)


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def root():
    """Return API status and links to UI and documentation."""
    return {
        "name": "ScholarSetu API",
        "status": "online",
        "description": "Scholarship schemes for Maharashtra engineering students (DTE Maharashtra + NSP)",
        "ui_url": "https://scholarsetu.streamlit.app",
        "docs_url": "/docs",
        "records": len(load_records()),
    }


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    """Tells you the service is running and how many schemes it has loaded."""
    return {"status": "ok", "records": len(load_records())}


@app.get("/records", response_model=list[Scheme])
def list_records(limit: int = Query(10, ge=1, le=100, description="How many schemes to return")):
    return load_records()[:limit]


@app.get("/records/{record_id}", response_model=Scheme)
def get_record(record_id: int):
    record = get_by_id(load_records(), record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Scheme {record_id} not found")
    return record


@app.get("/search", response_model=SearchResult)
def search_records(
    q: str = Query(..., min_length=2, max_length=200, description="Your question or keywords, e.g. OBC girl hostel"),
    limit: int = Query(5, ge=1, le=20, description="How many ranked results to return"),
):
    valid, err = validate_input(q, max_length=200)
    if not valid:
        raise HTTPException(status_code=422, detail=err)
    results = smart_search(q, top_k=limit)
    return {"query": q, "count": len(results), "results": results}


@app.get("/search/semantic", response_model=SemanticResult)
def semantic_search_records(
    q: str = Query(..., min_length=2, max_length=200, description="Your question, e.g. hostel allowance for farmers' children"),
    limit: int = Query(5, ge=1, le=20, description="How many chunks to return"),
):
    valid, err = validate_input(q, max_length=200)
    if not valid:
        raise HTTPException(status_code=422, detail=err)
    try:
        from app.vectorstore import (
            search as vector_search,  # loaded only when this endpoint is used
        )
        hits = vector_search(q, top_k=limit)
    except ImportError:
        raise HTTPException(status_code=503,
                            detail="Semantic search needs more packages. Run: pip install -r requirements.txt")
    except RuntimeError as error:  # includes EmbeddingError
        raise HTTPException(status_code=503, detail=str(error))
    return {"query": q, "count": len(hits), "results": hits}


@app.post("/questions", response_model=QuestionSaved, status_code=201)
def post_question(body: QuestionIn):
    valid, err = validate_input(body.question, max_length=500)
    if not valid:
        raise HTTPException(status_code=422, detail=err)
    try:
        return save_question(body.question, body.name)
    except OSError:
        raise HTTPException(status_code=500, detail="Could not save the question")


@app.post("/feedback", response_model=FeedbackSaved, status_code=201)
def post_feedback(body: FeedbackIn):
    """Save thumbs up/down feedback from the UI to data/feedback.json."""
    try:
        return save_feedback(body)
    except OSError:
        raise HTTPException(status_code=500, detail="Could not save feedback")


@app.get("/feedback", response_model=FeedbackSummary)
def list_feedback(limit: int = Query(20, ge=1, le=100)):
    """Return feedback counts and the most recent saved feedback items."""
    items = read_feedback()
    up = sum(1 for item in items if item.get("rating") == "up")
    down = sum(1 for item in items if item.get("rating") == "down")
    return {"total": len(items), "up": up, "down": down, "items": list(reversed(items))[:limit]}


@app.post("/stacking")
def check_stacking(body: StackingIn):
    """Check scholarship stacking conflicts and return the highest-value preference order."""
    records = load_records()
    if body.scheme_ids is not None:
        by_id = {r["id"]: r for r in records}
        missing = [sid for sid in body.scheme_ids if sid not in by_id]
        if missing:
            raise HTTPException(status_code=404, detail=f"Scheme id(s) not found: {missing}")
        selected = [by_id[sid] for sid in dict.fromkeys(body.scheme_ids)]
    else:
        selected = filter_eligible_records(
            records,
            category=body.category,
            gender=body.gender,
            family_income=body.family_income,
            has_disability=body.has_disability,
            is_hosteller=body.is_hosteller,
            include_abroad=body.include_abroad,
        )
    try:
        return analyze_stacking(
            selected,
            annual_fee=body.annual_fee,
            gender=body.gender,
            is_hosteller=body.is_hosteller,
            city_tier=body.city_tier,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn):
    valid, err = validate_input(body.question, max_length=500)
    if not valid:
        raise HTTPException(status_code=422, detail=err)
    try:
        reply, _ = answer_question(body.question, body.prompt_version)
    except LLMError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except OSError:
        raise HTTPException(status_code=500, detail="Could not read the prompt files")
    return reply


@app.post("/ask", response_model=AskOut)
def ask(body: AskIn):
    """Answer from the retrieved chunks, with citations. Says "I don't know" if the sources lack the answer."""
    valid, err = validate_input(body.question, max_length=500)
    if not valid:
        raise HTTPException(status_code=422, detail=err)

    start_t = time.perf_counter()
    try:
        from app.rag import (
            answer_question as rag_answer,  # loaded only when this endpoint is used
        )
        result = rag_answer(body.question)
    except ImportError:
        raise HTTPException(status_code=503,
                            detail="/ask needs more packages. Run: pip install -r requirements.txt")
    except LLMError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except RuntimeError as error:  # includes EmbeddingError and a missing index
        raise HTTPException(status_code=503, detail=str(error))

    duration_ms = (time.perf_counter() - start_t) * 1000
    usage = get_last_usage() if not result.get("cached") else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    logger.info(
        "POST /ask completed in %.2f ms | cached=%s | prompt_tokens=%d completion_tokens=%d total_tokens=%d",
        duration_ms,
        result.get("cached", False),
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
        usage.get("total_tokens", 0),
    )

    return {
        "question": body.question,
        "answer": result["answer"],
        "answerable": result["answerable"],
        "confidence": result["confidence"],
        "citations": result["citations"],
    }


@app.post("/agent", response_model=AgentOut)
def agent(body: AgentIn):
    """The LangGraph agent, with memory. Send a question (and a thread_id to continue a conversation).
    If the status is awaiting_approval, send the same thread_id with approve true or false."""
    if body.approve is not None and not body.thread_id:
        raise HTTPException(status_code=422, detail="Send the thread_id of the conversation that is waiting.")
    if body.approve is None and not body.question:
        raise HTTPException(status_code=422,
                            detail="Send a question, or approve (true or false) with a thread_id.")
    if body.question:
        valid, err = validate_input(body.question, max_length=500)
        if not valid:
            raise HTTPException(status_code=422, detail=err)
    try:
        from app.graph import (  # loaded only here
            AgentConflict,
            AgentNotFound,
            resume_turn,
            start_turn,
        )
    except ImportError:
        raise HTTPException(status_code=503,
                            detail="/agent needs more packages. Run: pip install -r requirements.txt")
    try:
        if body.approve is not None:
            return resume_turn(body.thread_id, body.approve)
        return start_turn(body.question, body.thread_id)
    except AgentNotFound as error:
        raise HTTPException(status_code=404, detail=str(error))
    except AgentConflict as error:
        raise HTTPException(status_code=409, detail=str(error))
    except LLMError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except RuntimeError as error:  # includes EmbeddingError and a missing index
        raise HTTPException(status_code=503, detail=str(error))


@app.get("/cache/stats", response_model=CacheStatsOut)
def cache_stats():
    """Return in-memory query cache statistics."""
    return query_cache.stats()


@app.post("/cache/clear")
def cache_clear():
    """Clear the in-memory query cache."""
    query_cache.clear()
    return {"status": "cleared"}
