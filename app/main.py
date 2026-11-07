import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.records import get_by_id, load_records
from app.smart_search import smart_search

QUESTIONS_JSON = Path(__file__).resolve().parent.parent / "data" / "questions.json"

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


class QuestionIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    name: Optional[str] = Field(default=None, max_length=100)


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


@app.post("/questions", response_model=QuestionSaved, status_code=201)
def post_question(body: QuestionIn):
    try:
        return save_question(body.question, body.name)
    except OSError:
        raise HTTPException(status_code=500, detail="Could not save the question")