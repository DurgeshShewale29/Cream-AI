"""Automated tests for Day 10: stacking warning, preference order, feedback API, RAG Q6 refusal, agent approval, and Streamlit UI."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app import main as api_main
from app.records import load_records
from app.stacking import (
    analyze_stacking,
    detect_mentioned_records,
    estimate_annual_value,
    filter_eligible_records,
)
from ui.app import build_stacking_dataframe, extract_agent_citations

ROOT_DIR = Path(__file__).resolve().parent.parent


class TestStackingRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_records()
        cls.by_id = {r["id"]: r for r in cls.records}

    def test_loaded_records_present(self):
        self.assertGreaterEqual(len(self.records), 7)

    def test_rajarshi_vs_pragati_high_fee_prefers_rajarshi(self):
        selected = [self.by_id[1], self.by_id[7], self.by_id[2]]
        result = analyze_stacking(selected, annual_fee=100_000, gender="Female", is_hosteller=True, city_tier="metro")

        self.assertTrue(result["has_conflict"])
        self.assertEqual(result["conflict_count"], 2)
        self.assertIn("MahaDBT pays only ONE", result["warning"])

        pref_ids = [p["id"] for p in result["preference_order"]]
        self.assertEqual(pref_ids, [1, 7])
        self.assertEqual(result["preference_order"][0]["estimated_value"], 100_000)
        self.assertEqual(result["preference_order"][1]["estimated_value"], 50_000)

        self.assertEqual(len(result["stackable_addons"]), 1)
        self.assertEqual(result["stackable_addons"][0]["id"], 2)
        self.assertEqual(result["max_combined_value"], 160_000)

        rows_by_id = {r["id"]: r for r in result["rows"]}
        self.assertFalse(rows_by_id[1]["can_stack"])
        self.assertFalse(rows_by_id[7]["can_stack"])
        self.assertTrue(rows_by_id[2]["can_stack"])
        self.assertTrue(rows_by_id[1]["conflicts_with"])

    def test_rajarshi_vs_pragati_low_fee_flips_preference_to_pragati(self):
        selected = [self.by_id[1], self.by_id[7]]
        result = analyze_stacking(selected, annual_fee=40_000, gender="Female")

        self.assertTrue(result["has_conflict"])
        pref_ids = [p["id"] for p in result["preference_order"]]
        self.assertEqual(pref_ids, [7, 1])

    def test_male_rajarshi_is_50_percent_and_pragati_filtered_out(self):
        eligible = filter_eligible_records(
            self.records,
            category="EWS",
            gender="Male",
            family_income=500_000,
            is_hosteller=True,
        )
        eligible_ids = {r["id"] for r in eligible}
        self.assertIn(1, eligible_ids)
        self.assertNotIn(7, eligible_ids)
        val, _ = estimate_annual_value(self.by_id[1], annual_fee=100_000, gender="Male")
        self.assertEqual(val, 50_000)

    def test_minority_conflict_ranks_part1_above_merit_cum_means(self):
        eligible = filter_eligible_records(
            self.records,
            category="Minority",
            gender="Male",
            family_income=200_000,
            is_hosteller=True,
        )
        result = analyze_stacking(eligible, annual_fee=80_000, gender="Male", is_hosteller=True)
        self.assertTrue(result["has_conflict"])
        pref_ids = [p["id"] for p in result["preference_order"]]
        self.assertEqual(pref_ids, [5, 3])

    def test_hostel_allowance_incompatible_with_foreign_only(self):
        selected = [self.by_id[4], self.by_id[2]]
        result = analyze_stacking(selected, annual_fee=200_000, gender="Female")
        self.assertTrue(result["has_conflict"])
        rows_by_id = {r["id"]: r for r in result["rows"]}
        self.assertFalse(rows_by_id[2]["can_stack"])

    def test_invalid_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            analyze_stacking([self.by_id[1]], annual_fee=-100)
        with self.assertRaises(ValueError):
            analyze_stacking([self.by_id[1]], gender="Other")
        with self.assertRaises(ValueError):
            analyze_stacking([self.by_id[1]], city_tier="village")

    def test_detect_mentioned_records_and_dataframe_format(self):
        answer = "Girls can apply for the Rajarshi Chhatrapati Shahu Maharaj scheme [1] or Pragati [2]."
        matched = detect_mentioned_records(answer, [], [], self.records)
        self.assertEqual({r["id"] for r in matched}, {1, 7})

        analysis = analyze_stacking(matched, annual_fee=100_000, gender="Female")
        df = build_stacking_dataframe(analysis)
        self.assertEqual(len(df), 2)
        self.assertTrue(all("Cannot stack" in s for s in df["Stacking Status"]))

    def test_extract_agent_citations(self):
        steps = [
            {
                "action": "search_scholarships",
                "input": "Pragati amount",
                "observation": "Rs 50,000 [1].\nSources: [1] Pragati Scholarship (https://dte.maharashtra.gov.in/pragati-scholarship-scheme/)",
            }
        ]
        cits = extract_agent_citations(steps, "")
        self.assertEqual(len(cits), 1)
        self.assertEqual(cits[0]["source"], "https://dte.maharashtra.gov.in/pragati-scholarship-scheme/")


class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api_main.app)

    def test_health(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertGreaterEqual(data["records"], 7)

    def test_feedback_post_and_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_file = Path(tmp) / "feedback.json"
            with patch.object(api_main, "FEEDBACK_JSON", temp_file):
                r1 = self.client.post("/feedback", json={
                    "question": "How much does Pragati give?",
                    "answer": "Rs 50,000 per year [1].",
                    "endpoint": "/ask",
                    "rating": "up",
                    "citations_count": 1,
                })
                self.assertEqual(r1.status_code, 201)
                self.assertEqual(r1.json()["id"], 1)

                r2 = self.client.post("/feedback", json={
                    "question": "Compare Rajarshi and Pragati",
                    "answer": "Comparison table...",
                    "endpoint": "/agent",
                    "rating": "down",
                    "comment": "Need hostel details too",
                })
                self.assertEqual(r2.status_code, 201)

                summary = self.client.get("/feedback").json()
                self.assertEqual(summary["total"], 2)
                self.assertEqual(summary["up"], 1)
                self.assertEqual(summary["down"], 1)

                bad = self.client.post("/feedback", json={
                    "question": "Test",
                    "answer": "Test",
                    "endpoint": "/ask",
                    "rating": "maybe",
                })
                self.assertEqual(bad.status_code, 422)

    def test_stacking_endpoint_by_ids_and_404(self):
        resp = self.client.post("/stacking", json={
            "scheme_ids": [1, 7, 2],
            "annual_fee": 100_000,
            "gender": "Female",
            "city_tier": "metro",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["has_conflict"])
        self.assertEqual(data["preference_order"][0]["id"], 1)
        self.assertEqual(data["max_combined_value"], 160_000)

        missing = self.client.post("/stacking", json={"scheme_ids": [999]})
        self.assertEqual(missing.status_code, 404)

    def test_ask_refuses_unanswerable_q6(self):
        from app import rag

        with patch.object(rag, "retrieve", return_value=[{"title": "X", "source": "https://x", "page": 1, "score": 0.5, "text": "Scholarship only"}]), \
             patch.object(rag, "ask_llm", return_value='{"answerable": false, "answer": "", "used_sources": [], "confidence": "low"}'):
            resp = self.client.post("/ask", json={"question": "What is the hostel fee at Sanjivani College of Engineering?"})
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            self.assertFalse(body["answerable"])
            self.assertIn("I don't know", body["answer"])
            self.assertEqual(body["citations"], [])

    def test_agent_approval_pause_and_resume(self):
        from app import graph as agent_graph

        agent_graph.get_graph.cache_clear()
        decisions = iter([
            {"action": "compare_schemes", "input": ["Rajarshi", "Pragati"]},
            {"action": "final_answer", "input": "Here is the comparison table for Rajarshi and Pragati."},
        ])
        with patch.object(agent_graph, "decide", side_effect=lambda *args, **kwargs: next(decisions)):
            r1 = self.client.post("/agent", json={"question": "Compare Rajarshi and Pragati"})
            self.assertEqual(r1.status_code, 200)
            d1 = r1.json()
            self.assertEqual(d1["status"], "awaiting_approval")
            self.assertEqual(d1["pending_action"]["action"], "compare_schemes")

            r2 = self.client.post("/agent", json={"thread_id": d1["thread_id"], "approve": True})
            self.assertEqual(r2.status_code, 200)
            d2 = r2.json()
            self.assertEqual(d2["status"], "answered")
            self.assertIn("compare_schemes", d2["tools_used"])
            self.assertIn("Rajarshi", d2["answer"])


class TestStreamlitUI(unittest.TestCase):
    def test_streamlit_renders_stacking_warning_and_chat_without_error(self):
        mock_ask_reply = {
            "question": "I am a girl studying engineering. Which schemes cover my tuition fee?",
            "answer": "Girl students qualify for Rajarshi Chhatrapati Shahu Maharaj [1] and Pragati [2].",
            "answerable": True,
            "confidence": "high",
            "citations": [
                {
                    "n": 1,
                    "title": "Rajarshi Chhatrapati Shahu Maharaj Education Fee Scholarship Scheme",
                    "source": "https://dte.maharashtra.gov.in/rajarshi-chhatrapati-shahu-maharaj",
                    "page": 1,
                    "score": 0.78,
                },
                {
                    "n": 2,
                    "title": "Pragati Scholarship Scheme for Girls (Degree/Diploma)",
                    "source": "https://dte.maharashtra.gov.in/pragati-scholarship-scheme/",
                    "page": 1,
                    "score": 0.71,
                },
            ],
        }
        with patch("ui.app.check_api_health", return_value=(True, "Online (7 schemes)")), \
             patch("ui.app.call_ask", return_value=mock_ask_reply):
            at = AppTest.from_file(str(ROOT_DIR / "ui" / "app.py"), default_timeout=15)
            at.run()
            self.assertFalse(at.exception, f"Streamlit raised an exception: {at.exception}")
            warnings = [w.value for w in at.warning]
            self.assertTrue(any("Stacking Warning" in w for w in warnings))
            self.assertGreaterEqual(len(at.dataframe), 1)


if __name__ == "__main__":
    unittest.main()
