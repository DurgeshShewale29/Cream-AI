"""Pytest tests for compare_schemes agent tool, hand-written agent loop, and LangGraph rejection flow."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app import agent_loop, graph
from app.main import app
from app.tools import ToolError, compare_schemes

client = TestClient(app)


def test_compare_schemes_returns_markdown_table():
    table = compare_schemes(["Rajarshi", "Pragati"])
    assert "| **Benefit** |" in table
    assert "| **Eligibility** |" in table
    assert "| **Documents** |" in table
    assert "| **Apply link** |" in table
    assert "Rajarshi Chhatrapati Shahu Maharaj" in table
    assert "Pragati Scholarship Scheme" in table


def test_compare_schemes_accepts_comma_string_and_close_spelling():
    table = compare_schemes("Rajarshii, Panjabrao")
    assert "Rajarshi Chhatrapati Shahu Maharaj" in table
    assert "Punjabrao Deshmukh" in table


@pytest.mark.parametrize(
    "bad_input",
    [
        ["Rajarshi"],
        ["Rajarshi", "Pragati", "Punjabrao", "Merit-Cum-Means", "Foreign"],
        ["Rajarshi", "Rajarshi"],
        ["Rajarshi", "NonExistentSchemeXYZ"],
        ["Ra", "Pragati"],
        12345,
    ],
)
def test_compare_schemes_validates_inputs(bad_input):
    with pytest.raises(ToolError):
        compare_schemes(bad_input)


def test_agent_loop_calls_compare_schemes_with_fake_llm(monkeypatch):
    replies = iter([
        json.dumps({
            "thought": "Compare the two requested schemes.",
            "action": "compare_schemes",
            "input": ["Rajarshi", "Pragati"],
        }),
        json.dumps({
            "thought": "Return the comparison table.",
            "action": "final_answer",
            "input": "Here is the comparison between Rajarshi and Pragati.",
        }),
    ])
    monkeypatch.setattr(agent_loop, "ask_llm", lambda *args, **kwargs: next(replies))

    result = agent_loop.run_agent("Compare Rajarshi and Pragati")
    assert result["tools_used"] == ["compare_schemes"]
    assert len(result["steps"]) == 1
    assert "| **Benefit** |" in result["steps"][0]["observation"]
    assert "Rajarshi" in result["answer"]


def test_agent_loop_stops_at_max_steps(monkeypatch):
    monkeypatch.setattr(
        agent_loop,
        "ask_llm",
        lambda *args, **kwargs: json.dumps({
            "thought": "Keep comparing forever.",
            "action": "compare_schemes",
            "input": ["Rajarshi", "Pragati"],
        }),
    )

    result = agent_loop.run_agent("Loop test")
    assert len(result["steps"]) == agent_loop.MAX_STEPS
    assert result["answer"] == agent_loop.STEP_LIMIT_TEXT


def test_langgraph_agent_rejection_skips_tool(monkeypatch):
    graph.get_graph.cache_clear()
    decisions = iter([
        {"action": "compare_schemes", "input": ["Rajarshi", "Pragati"]},
        {"action": "final_answer", "input": "Understood — I skipped comparing the schemes."},
    ])
    monkeypatch.setattr(graph, "decide", lambda *args, **kwargs: next(decisions))

    r1 = client.post("/agent", json={"question": "Compare Rajarshi and Pragati"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["status"] == "awaiting_approval"

    r2 = client.post("/agent", json={"thread_id": d1["thread_id"], "approve": False})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["status"] == "answered"
    assert "skipped" in d2["answer"].lower()
    assert "did not approve" in d2["steps"][0]["observation"].lower()
