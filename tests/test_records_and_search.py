"""Pytest tests for records loading, keyword/TF-IDF search, and /records + /search endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Record
from app.records import count_by, get_by_id, load_record_objects, load_records, search
from app.smart_search import SmartSearch, smart_search

client = TestClient(app)


def test_load_records_returns_verified_schemes():
    records = load_records()
    assert len(records) >= 7
    required = {
        "id",
        "scheme_name",
        "department",
        "eligible_category",
        "income_limit",
        "benefit",
        "source_url",
        "verified",
    }
    for record in records:
        assert required.issubset(record.keys())
        assert record["verified"] is True


def test_load_record_objects_builds_dataclasses():
    objects = load_record_objects()
    assert len(objects) >= 7
    first = objects[0]
    assert isinstance(first, Record)
    assert isinstance(first.id, int)
    assert first.scheme_name


def test_records_search_count_by_and_get_by_id():
    records = load_records()
    girl_hits = search(records, "Pragati")
    assert len(girl_hits) == 1
    assert "Pragati" in girl_hits[0]["scheme_name"]

    assert search(records, "no_such_scholarship_xyz") == []

    dept_counts = count_by(records, "department")
    assert sum(dept_counts.values()) == len(records)

    first = get_by_id(records, 1)
    assert first is not None
    assert first["id"] == 1
    assert get_by_id(records, 9999) is None


@pytest.mark.parametrize(
    ("query", "expected_fragment"),
    [
        ("Rajarshi EWS education fee", "Rajarshi"),
        ("Pragati girls lump sum 50,000", "Pragati"),
        ("Punjabrao hostel subsistence allowance", "Punjabrao"),
        ("students with disabilities 1,90,000", "Disabilities"),
    ],
)
def test_smart_search_ranks_expected_scheme_first(query: str, expected_fragment: str):
    hits = smart_search(query, top_k=3)
    assert hits
    assert expected_fragment.lower() in hits[0]["scheme_name"].lower()
    assert 0.0 < hits[0]["score"] <= 1.0


def test_smart_search_blank_or_empty_index_returns_empty():
    assert smart_search("   ") == []
    empty_index = SmartSearch([])
    assert empty_index.search("EWS") == []


def test_records_and_search_api_endpoints():
    r_list = client.get("/records?limit=3")
    assert r_list.status_code == 200
    assert len(r_list.json()) == 3

    r_one = client.get("/records/1")
    assert r_one.status_code == 200
    assert r_one.json()["id"] == 1

    r_missing = client.get("/records/9999")
    assert r_missing.status_code == 404

    r_search = client.get("/search", params={"q": "Pragati girls"})
    assert r_search.status_code == 200
    body = r_search.json()
    assert body["count"] >= 1
    assert "Pragati" in body["results"][0]["scheme_name"]

    r_short = client.get("/search", params={"q": "a"})
    assert r_short.status_code == 422
