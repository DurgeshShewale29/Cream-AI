"""Pytest tests for /health and /ask using a fake LLM (citations, refusals, and error handling)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app import rag
from app.llm import LLMError
from app.main import app

client = TestClient(app)

FAKE_CHUNKS = [
    {
        "title": "Pragati Scholarship Scheme for Girls (Degree/Diploma)",
        "source": "https://dte.maharashtra.gov.in/pragati-scholarship-scheme/",
        "page": 1,
        "score": 0.82,
        "text": "Eligible girl students receive a lump sum amount of Rs 50,000 per annum. Annual family income limit is up to Rs 8 lakh.",
    },
    {
        "title": "Rajarshi Chhatrapati Shahu Maharaj Education Fee Scholarship Scheme",
        "source": "https://dte.maharashtra.gov.in/rajarshi-chhatrapati-shahu-maharaj",
        "page": 1,
        "score": 0.74,
        "text": "Girl students from EBC, EWS and SEBC categories with family income up to Rs 8 lakh get 100% tuition and exam fees.",
    },
]


def test_health_endpoint_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["records"] >= 7


def test_ask_with_fake_llm_returns_grounded_citations(monkeypatch):
    def fake_retrieve(question, top_k=rag.TOP_K, chunk_words=rag.RAG_CHUNK_WORDS):
        return FAKE_CHUNKS

    def fake_ask_llm(system_prompt, user_message, **kwargs):
        return json.dumps({
            "answerable": True,
            "answer": "Pragati gives Rs 50,000 per year to eligible girl students [1].",
            "used_sources": [1],
            "confidence": "high",
        })

    monkeypatch.setattr(rag, "retrieve", fake_retrieve)
    monkeypatch.setattr(rag, "ask_llm", fake_ask_llm)

    resp = client.post("/ask", json={"question": "How much money does Pragati give?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answerable"] is True
    assert body["confidence"] == "high"
    assert "50,000" in body["answer"]
    assert len(body["citations"]) == 1
    assert body["citations"][0]["n"] == 1
    assert "pragati-scholarship-scheme" in body["citations"][0]["source"]


def test_ask_rejects_uncited_fake_llm_answer(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda *args, **kwargs: FAKE_CHUNKS)
    monkeypatch.setattr(
        rag,
        "ask_llm",
        lambda *args, **kwargs: json.dumps({
            "answerable": True,
            "answer": "Pragati gives Rs 50,000 per year without any source marker.",
            "used_sources": [],
            "confidence": "high",
        }),
    )

    resp = client.post("/ask", json={"question": "How much money does Pragati give?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answerable"] is False
    assert "I don't know" in body["answer"]
    assert body["citations"] == []


def test_ask_refuses_unanswerable_q6_with_fake_llm(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda *args, **kwargs: FAKE_CHUNKS)
    monkeypatch.setattr(
        rag,
        "ask_llm",
        lambda *args, **kwargs: json.dumps({
            "answerable": False,
            "answer": "",
            "used_sources": [],
            "confidence": "low",
        }),
    )

    resp = client.post(
        "/ask",
        json={"question": "What is the hostel fee at Sanjivani College of Engineering?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answerable"] is False
    assert "I don't know" in body["answer"]
    assert body["citations"] == []


def test_ask_skips_llm_when_retrieval_score_too_low(monkeypatch):
    low_chunks = [{**FAKE_CHUNKS[0], "score": 0.05}]
    called = {"llm": False}

    def should_not_be_called(*args, **kwargs):
        called["llm"] = True
        return "{}"

    monkeypatch.setattr(rag, "retrieve", lambda *args, **kwargs: low_chunks)
    monkeypatch.setattr(rag, "ask_llm", should_not_be_called)

    resp = client.post("/ask", json={"question": "Completely unrelated weather query?"})
    assert resp.status_code == 200
    body = resp.json()
    assert called["llm"] is False
    assert body["answerable"] is False
    assert "I don't know" in body["answer"]


def test_ask_handles_invalid_json_and_llm_error(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda *args, **kwargs: FAKE_CHUNKS)
    monkeypatch.setattr(rag, "ask_llm", lambda *args, **kwargs: "not valid json at all")

    resp = client.post("/ask", json={"question": "How much does Pragati give?"})
    assert resp.status_code == 200
    assert resp.json()["answerable"] is False

    def raise_llm_error(*args, **kwargs):
        raise LLMError("Rate limit reached")

    monkeypatch.setattr(rag, "ask_llm", raise_llm_error)
    err_resp = client.post("/ask", json={"question": "How much does Pragati give?"})
    assert err_resp.status_code == 503
    assert "Rate limit" in err_resp.json()["detail"]
