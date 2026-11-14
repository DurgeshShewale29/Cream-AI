import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.llm import LLMError, ask_llm
from app.records import get_by_id, load_records
from app.smart_search import smart_search

BASE_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_JSON = BASE_DIR / "data" / "questions.json"
PROMPTS_DIR = BASE_DIR / "prompts"

app = FastAPI(
    title="ScholarSetu API",
    description="Scholarship schemes for Maharashtra engineering students (DTE Maharashtra + NSP).",
    version="0.1.0",
)


class Scheme(BaseModel):
    id: int
    scheme_name: str
    department: str
    eligible_category: str
    income_limit: Optional[int] = None
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
    name: Optional[str] = Field(default=None, max_length=100)


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    prompt_version: Literal["v1", "v2"] = "v2"


class ChatOut(BaseModel):
    answer: str
    confidence: Literal["high", "medium", "low"]
    follow_up: str


class QuestionSaved(BaseModel):
    id: int
    question: str
    name: Optional[str] = None
    created_at: str


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
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    questions.append(entry)
    with open(QUESTIONS_JSON, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
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


@app.get("/health")
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
    q: str = Query(..., min_length=2, description="Your question or keywords, e.g. OBC girl hostel"),
    limit: int = Query(5, ge=1, le=20, description="How many ranked results to return"),
):
    results = smart_search(q, top_k=limit)
    return {"query": q, "count": len(results), "results": results}


@app.get("/search/semantic", response_model=SemanticResult)
def semantic_search_records(
    q: str = Query(..., min_length=2, description="Your question, e.g. hostel allowance for farmers' children"),
    limit: int = Query(5, ge=1, le=20, description="How many chunks to return"),
):
    try:
        from app.vectorstore import search as vector_search  # loaded only when this endpoint is used
        hits = vector_search(q, top_k=limit)
    except ImportError:
        raise HTTPException(status_code=503,
                            detail="Semantic search needs more packages. Run: pip install -r requirements.txt")
    except RuntimeError as error:  # includes EmbeddingError
        raise HTTPException(status_code=503, detail=str(error))
    return {"query": q, "count": len(hits), "results": hits}


@app.post("/questions", response_model=QuestionSaved, status_code=201)
def post_question(body: QuestionIn):
    try:
        return save_question(body.question, body.name)
    except OSError:
        raise HTTPException(status_code=500, detail="Could not save the question")


@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn):
    try:
        reply, _ = answer_question(body.question, body.prompt_version)
    except LLMError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except OSError:
        raise HTTPException(status_code=500, detail="Could not read the prompt files")
    return reply