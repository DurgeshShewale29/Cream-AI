"""ScholarSetu Streamlit Chat UI with Citations, Feedback & Stacking Warning."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

UI_DIR = Path(__file__).resolve().parent
ROOT_DIR = UI_DIR.parent
logger = logging.getLogger(__name__)

DEFAULT_RENDER_API = "https://cream-ai.onrender.com"


def resolve_api_url() -> str:
    """Resolve API URL: custom env/secrets -> local uvicorn if running -> production Render."""
    custom = os.getenv("SCHOLARSETU_API_URL")
    if not custom:
        try:
            if hasattr(st, "secrets") and "SCHOLARSETU_API_URL" in st.secrets:
                custom = str(st.secrets["SCHOLARSETU_API_URL"])
        except (KeyError, AttributeError, FileNotFoundError, StreamlitSecretNotFoundError):
            logger.debug("SCHOLARSETU_API_URL not present in st.secrets")
    if custom:
        return custom.rstrip("/")

    # If local uvicorn server is running and healthy, use it
    try:
        r = requests.get("http://127.0.0.1:8000/health", timeout=0.8)
        if r.status_code == 200:
            return "http://127.0.0.1:8000"
    except requests.RequestException:
        logger.debug("Local uvicorn server unreachable; falling back to production Render API")

    # Default fallback: live production Render API
    return DEFAULT_RENDER_API


API_URL = resolve_api_url()
FEEDBACK_JSON = ROOT_DIR / "data" / "feedback.json"
API_TIMEOUT = 120


def _load_app_modules():
    """Import app.* safely even when Streamlit puts ui/ ahead of the project root."""
    sys.path = [p for p in sys.path if Path(p or ".").resolve() != UI_DIR]
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    if "app" in sys.modules and getattr(sys.modules["app"], "__file__", "") == str(Path(__file__).resolve()):
        del sys.modules["app"]
    from app.records import load_records
    from app.stacking import (
        ALL_CATEGORIES,
        analyze_stacking,
        detect_mentioned_records,
        filter_eligible_records,
    )
    return load_records, ALL_CATEGORIES, analyze_stacking, detect_mentioned_records, filter_eligible_records

SAMPLE_QUESTIONS = [
    ("Rajarshi EWS Rs 6L check", "My family income is Rs 6 lakh and I am from an EWS family. Can I get the Rajarshi Chhatrapati Shahu Maharaj scholarship?"),
    ("Compare Rajarshi & Pragati", "Compare Rajarshi and Pragati"),
    ("Farmer hostel allowance", "How much hostel allowance can I get if my parents are small-land farmers?"),
    ("Minority Rs 2L income", "I belong to a minority community and my family income is Rs 2 lakh. Which scholarship can I apply for?"),
    ("Q6 Hostel fee (unanswerable)", "What is the hostel fee at Sanjivani College of Engineering?"),
]


def format_rupees(amount: int | None) -> str:
    if amount is None:
        return "Not stated"
    return f"Rs {int(amount):,}"


def extract_agent_citations(steps: list[dict], answer: str = "") -> list[dict]:
    """Pull cited sources out of agent tool steps or the final answer."""
    citations: list[dict] = []
    seen: set[str] = set()

    def add_citation(title: str, source: str) -> None:
        url = source.strip().rstrip(".,);]")
        if not url or url in seen:
            return
        seen.add(url)
        citations.append({
            "n": len(citations) + 1,
            "title": title.strip() or url,
            "source": url,
            "page": 1,
            "score": None,
        })

    pattern = re.compile(r"\[\d+\]\s+([^\(\n]+?)\s*\((https?://[^\s\)]+)\)")
    for step in steps or []:
        obs = str(step.get("observation") or "")
        for title, url in pattern.findall(obs):
            add_citation(title, url)
        for url in re.findall(r"https?://[^\s\|\)\]>]+", obs):
            add_citation("Official Scheme Page", url)

    for url in re.findall(r"https?://[^\s\|\)\]>]+", answer or ""):
        add_citation("Official Scheme Page", url)

    return citations


def check_api_health(api_url: str) -> tuple[bool, str]:
    try:
        resp = requests.get(f"{api_url.rstrip('/')}/health", timeout=8)
        resp.raise_for_status()
        data = resp.json()
        return True, f"Online ({data.get('records', 0)} schemes)"
    except (requests.RequestException, ValueError) as error:
        return False, f"Offline ({error.__class__.__name__})"


def call_ask(api_url: str, question: str) -> dict:
    resp = requests.post(
        f"{api_url.rstrip('/')}/ask",
        json={"question": question},
        timeout=API_TIMEOUT,
    )
    if resp.status_code != 200:
        detail = _extract_error(resp)
        raise RuntimeError(f"/ask failed ({resp.status_code}): {detail}")
    return resp.json()


def call_agent(
    api_url: str,
    question: str | None = None,
    thread_id: str | None = None,
    approve: bool | None = None,
) -> dict:
    payload: dict[str, Any] = {}
    if question is not None:
        payload["question"] = question
    if thread_id is not None:
        payload["thread_id"] = thread_id
    if approve is not None:
        payload["approve"] = approve
    resp = requests.post(
        f"{api_url.rstrip('/')}/agent",
        json=payload,
        timeout=API_TIMEOUT,
    )
    if resp.status_code != 200:
        detail = _extract_error(resp)
        raise RuntimeError(f"/agent failed ({resp.status_code}): {detail}")
    return resp.json()


def _extract_error(resp: requests.Response) -> str:
    try:
        return str(resp.json().get("detail", resp.text[:200]))
    except (ValueError, TypeError, AttributeError):
        return resp.text[:200]


def save_feedback_local(entry: dict) -> dict:
    """Fallback writer to data/feedback.json when the FastAPI feedback route is unavailable."""
    try:
        items = json.loads(FEEDBACK_JSON.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        items = []
    saved = {
        "id": len(items) + 1,
        **entry,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    items.append(saved)
    FEEDBACK_JSON.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_JSON.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    return saved


def submit_feedback(api_url: str, payload: dict) -> dict:
    """Save thumbs up/down via POST /feedback, falling back to local data/feedback.json."""
    try:
        resp = requests.post(f"{api_url.rstrip('/')}/feedback", json=payload, timeout=5)
        if resp.status_code in (200, 201):
            return resp.json()
    except (requests.RequestException, ValueError) as error:
        logger.warning("Feedback API unavailable, saving locally: %s", error)
    return save_feedback_local(payload)


def _compact_status(row: dict) -> str:
    if not row["can_stack"]:
        if "foreign study" in row["stacking_status"].lower():
            return "⚠️ Cannot stack (Abroad only)"
        return "⚠️ Cannot stack (MahaDBT pays 1)"
    if "Add-on" in row["preference_label"]:
        return "✅ Can stack (Hostel add-on)"
    return "✅ Eligible (No conflict)"


def build_stacking_dataframe(analysis: dict) -> pd.DataFrame:
    """Turn analyze_stacking() output into a concise 6-column DataFrame that fits on screen."""
    table_rows = []
    for row in analysis.get("rows", []):
        conflicts = ", ".join(row["conflicts_with"]) if row["conflicts_with"] else "None"
        table_rows.append({
            "Pref": row["preference_label"],
            "Scheme": row["short_name"],
            "Portal": row["portal"],
            "Est. / yr": format_rupees(row["estimated_value"]),
            "Stacking Status": _compact_status(row),
            "Cannot Take With": conflicts,
        })
    return pd.DataFrame(table_rows)


def _highlight_stacking_row(row: pd.Series) -> list[str]:
    status = str(row.get("Stacking Status", ""))
    if "Cannot stack" in status:
        return ["background-color: rgba(255, 193, 7, 0.16)"] * len(row)
    if "Can stack" in status:
        return ["background-color: rgba(40, 167, 69, 0.16)"] * len(row)
    return [""] * len(row)


def render_stacking_panel(
    analysis: dict,
    heading: str = "Stacking Warning & Highest-Value Preference Order",
    compact: bool = False,
) -> None:
    """Render the signature Stacking Warning banner, full-width results table and preference order."""
    if heading:
        st.subheader(heading)

    rows = analysis.get("rows", [])
    if not rows:
        st.info("No schemes matched the current selection. Adjust your profile or pick schemes below.")
        return

    if analysis["has_conflict"]:
        st.warning(analysis["warning"], icon="⚠️")
    else:
        st.success("No stacking conflict among the shown schemes.", icon="✅")

    df = build_stacking_dataframe(analysis)
    styled = df.style.apply(_highlight_stacking_row, axis=1)
    st.dataframe(
        styled,
        width="stretch",
        hide_index=True,
    )

    pref_order = analysis.get("preference_order", [])
    addons = analysis.get("stackable_addons", [])

    order_col, summary_col = st.columns([1.45, 1.0], gap="large")
    with order_col:
        if pref_order:
            st.markdown("#### Suggested Highest-Value Preference Order")
            for item in pref_order:
                badge = "Recommended Pref #1" if item["rank"] == 1 else f"Backup Pref #{item['rank']}"
                st.markdown(
                    f"**{item['rank']}. {item['short_name']}** ({item['portal']}) — "
                    f"**{format_rupees(item['estimated_value'])}/yr** · *{badge}*  \n"
                    f"<span style='opacity:0.78;font-size:0.88em;'>{item['value_note']}</span>",
                    unsafe_allow_html=True,
                )
        if addons:
            st.markdown("#### Stackable Add-On (Can Be Taken Together)")
            for addon in addons:
                st.markdown(
                    f"**+ {addon['short_name']}** ({addon['portal']}) — "
                    f"**{format_rupees(addon['estimated_value'])}/yr**  \n"
                    f"<span style='opacity:0.78;font-size:0.88em;'>{addon['value_note']}</span>",
                    unsafe_allow_html=True,
                )

    with summary_col:
        if not compact:
            st.markdown("#### Summary")
        m1, m2 = st.columns(2)
        m1.metric("Schemes", len(rows))
        m2.metric("Conflicting", analysis.get("conflict_count", 0))
        st.metric("Max Combined Benefit / yr", format_rupees(analysis.get("max_combined_value", 0)))


def render_citations(citations: list[dict], expanded: bool = False) -> None:
    if not citations:
        return
    with st.expander(f"Citations ({len(citations)})", expanded=expanded):
        for c in citations:
            score_part = f" · score {c['score']:.2f}" if c.get("score") is not None else ""
            st.markdown(
                f"- **[{c['n']}] {c['title']}** (page {c.get('page', 1)}{score_part}) — "
                f"[{c['source']}]({c['source']})"
            )


def render_agent_steps(steps: list[dict]) -> None:
    if not steps:
        return
    with st.expander(f"Agent steps ({len(steps)})", expanded=False):
        for idx, step in enumerate(steps, start=1):
            st.markdown(f"**Step {idx}:** `{step['action']}({step['input']})`")
            st.caption(str(step.get("observation", ""))[:300])


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None
    if "pending_question" not in st.session_state:
        st.session_state.pending_question = None
    if "last_matched_ids" not in st.session_state:
        st.session_state.last_matched_ids = []
    if "feedback_saved" not in st.session_state:
        st.session_state.feedback_saved = {}


def handle_question(question: str, api_url: str, mode: str, records: list[dict]) -> None:
    _, _, _, detect_mentioned_records, _ = _load_app_modules()
    question = question.strip()
    if len(question) < 3:
        st.warning("Please enter at least 3 characters.")
        return

    st.session_state.messages.append({"role": "user", "content": question})

    try:
        if mode == "/ask":
            data = call_ask(api_url, question)
            citations = data.get("citations", [])
            matched = detect_mentioned_records(data.get("answer", ""), citations, [], records)
            st.session_state.last_matched_ids = [r["id"] for r in matched]
            st.session_state.messages.append({
                "role": "assistant",
                "endpoint": "/ask",
                "question": question,
                "content": data.get("answer", ""),
                "answerable": data.get("answerable", False),
                "confidence": data.get("confidence", "low"),
                "citations": citations,
                "steps": [],
                "status": "answered",
                "pending_action": None,
                "thread_id": None,
                "matched_ids": [r["id"] for r in matched],
            })
        else:
            data = call_agent(api_url, question=question, thread_id=st.session_state.thread_id)
            st.session_state.thread_id = data.get("thread_id")
            steps = data.get("steps", [])
            answer = data.get("answer") or ""
            citations = extract_agent_citations(steps, answer)
            matched = detect_mentioned_records(answer, citations, steps, records)
            if matched:
                st.session_state.last_matched_ids = [r["id"] for r in matched]
            st.session_state.messages.append({
                "role": "assistant",
                "endpoint": "/agent",
                "question": question,
                "content": answer,
                "answerable": True,
                "confidence": None,
                "citations": citations,
                "steps": steps,
                "tools_used": data.get("tools_used", []),
                "turns": data.get("turns", 0),
                "status": data.get("status", "answered"),
                "pending_action": data.get("pending_action"),
                "thread_id": data.get("thread_id"),
                "matched_ids": [r["id"] for r in matched],
            })
    except (requests.RequestException, RuntimeError, ValueError) as error:
        st.session_state.messages.append({
            "role": "assistant",
            "endpoint": mode,
            "question": question,
            "content": f"Request error: {error}",
            "answerable": False,
            "confidence": "low",
            "citations": [],
            "steps": [],
            "status": "error",
            "pending_action": None,
            "thread_id": st.session_state.thread_id,
            "matched_ids": [],
        })


def handle_approval(msg_index: int, approve: bool, api_url: str, records: list[dict]) -> None:
    _, _, _, detect_mentioned_records, _ = _load_app_modules()
    msg = st.session_state.messages[msg_index]
    try:
        data = call_agent(api_url, thread_id=msg["thread_id"], approve=approve)
        steps = data.get("steps", [])
        answer = data.get("answer") or ""
        citations = extract_agent_citations(steps, answer)
        matched = detect_mentioned_records(answer, citations, steps, records)
        if matched:
            st.session_state.last_matched_ids = [r["id"] for r in matched]
        msg.update({
            "content": answer,
            "citations": citations,
            "steps": steps,
            "tools_used": data.get("tools_used", []),
            "turns": data.get("turns", 0),
            "status": data.get("status", "answered"),
            "pending_action": data.get("pending_action"),
            "matched_ids": [r["id"] for r in matched],
        })
    except (requests.RequestException, RuntimeError, ValueError) as error:
        msg["status"] = "error"
        msg["content"] = f"Approval error: {error}"


def main() -> None:
    st.set_page_config(
        page_title="ScholarSetu — Maharashtra Engineering Scholarships",
        page_icon="🎓",
        layout="wide",
    )
    init_state()
    load_records, ALL_CATEGORIES, analyze_stacking, _, filter_eligible_records = _load_app_modules()
    records = load_records()
    records_by_id = {r["id"]: r for r in records}
    api_url = resolve_api_url()

    with st.sidebar:
        st.title("🎓 ScholarSetu")
        st.caption("Maharashtra Engineering Scholarships (DTE MahaDBT + NSP/AICTE)")

        ok, _ = check_api_health(api_url)
        if not ok:
            st.error(
                f"Backend server is offline or waking up ({api_url}). "
                "If on Render free tier, it spins up in ~30s. Please wait a moment and refresh."
            )

        mode_label = st.radio(
            "Assistant mode",
            options=["Quick Q&A (Citations)", "Smart Agent (Compare & Memory)"],
            index=0,
        )
        mode = "/ask" if mode_label.startswith("Quick") else "/agent"

        if mode == "/agent" and st.button("New agent conversation", width="stretch"):
            st.session_state.thread_id = None
            st.rerun()

        st.divider()
        st.subheader("Student Profile")
        category = st.selectbox("Category", options=list(ALL_CATEGORIES), index=1)
        gender = st.radio("Gender", options=["Female", "Male"], horizontal=True, index=0)
        family_income = st.number_input(
            "Annual family income (Rs)",
            min_value=0,
            max_value=2_000_000,
            value=400_000,
            step=50_000,
        )
        annual_fee = st.number_input(
            "Annual college tuition + exam fee (Rs)",
            min_value=0,
            max_value=500_000,
            value=100_000,
            step=10_000,
            help="Ranks Rajarshi (50%/100% fee) against fixed-amount schemes like Pragati (Rs 50,000).",
        )
        city_label = st.selectbox(
            "College city tier",
            options=["Metro (Mumbai/Pune/Thane/Nagpur)", "Non-metro city"],
            index=0,
        )
        city_tier = "metro" if city_label.startswith("Metro") else "non_metro"
        is_hosteller = st.checkbox("Staying in hostel", value=True)
        has_disability = st.checkbox("Student with disability", value=False)
        include_abroad = st.checkbox("Include foreign study scheme", value=False)

    st.markdown("## 🎓 ScholarSetu — Scholarship Chat & Stacking Advisor")
    st.caption(
        "Grounded answers from official DTE Maharashtra & NSP pages, with citations, "
        "thumbs up/down feedback, and MahaDBT stacking conflict warnings."
    )

    tab_chat, tab_stacking = st.tabs([
        "💬 Scholarship Chat",
        "⚠️ Stacking Warning & Preference Order",
    ])

    with tab_chat:
        row1 = st.columns(3)
        for col, (label, q_text) in zip(row1, SAMPLE_QUESTIONS[:3]):
            if col.button(label, key=f"sample_{label}", width="stretch"):
                st.session_state.pending_question = q_text
        row2 = st.columns(2)
        for col, (label, q_text) in zip(row2, SAMPLE_QUESTIONS[3:]):
            if col.button(label, key=f"sample_{label}", width="stretch"):
                st.session_state.pending_question = q_text

        if st.session_state.pending_question:
            queued = st.session_state.pending_question
            st.session_state.pending_question = None
            with st.spinner("Searching official scholarship sources..."):
                handle_question(queued, api_url, mode, records)
            st.rerun()

        if not st.session_state.messages:
            st.info(
                "Ask a scholarship question below or pick a quick prompt above. "
                "Switch to Smart Agent in the sidebar to compare schemes with approval."
            )

        for idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                if msg["role"] == "user":
                    st.markdown(msg["content"])
                    continue

                is_latest = idx == len(st.session_state.messages) - 1
                ep = msg.get("endpoint", "/ask")
                if ep == "/ask":
                    conf = msg.get("confidence", "low")
                    ans_tag = "Grounded answer" if msg.get("answerable") else "Not found in sources"
                    st.caption(f"{ans_tag} · confidence: **{conf}**")
                else:
                    tools_str = ", ".join(msg.get("tools_used") or []) or "none"
                    st.caption(f"Smart Agent · tools: `{tools_str}`")

                if msg.get("status") == "awaiting_approval":
                    pending = msg.get("pending_action") or {}
                    st.warning(
                        f"**Approval required:** the agent wants to run "
                        f"`{pending.get('action')}({pending.get('input')})`."
                    )
                    ap1, ap2, _ = st.columns([0.25, 0.25, 0.5])
                    if ap1.button("✅ Approve & Run", key=f"approve_{idx}", width="stretch"):
                        with st.spinner("Running approved tool..."):
                            handle_approval(idx, True, api_url, records)
                        st.rerun()
                    if ap2.button("❌ Reject", key=f"reject_{idx}", width="stretch"):
                        with st.spinner("Sending rejection..."):
                            handle_approval(idx, False, api_url, records)
                        st.rerun()
                else:
                    st.markdown(msg.get("content", ""))

                render_citations(msg.get("citations", []), expanded=is_latest)
                render_agent_steps(msg.get("steps", []))

                matched_here = [records_by_id[rid] for rid in msg.get("matched_ids", []) if rid in records_by_id]
                if len(matched_here) >= 2:
                    inline_check = analyze_stacking(
                        matched_here,
                        annual_fee=int(annual_fee),
                        gender=gender,
                        is_hosteller=is_hosteller,
                        city_tier=city_tier,
                    )
                    if inline_check["has_conflict"]:
                        render_stacking_panel(
                            inline_check,
                            heading="Stacking Warning for Matched Schemes",
                            compact=True,
                        )

                if msg.get("status") == "answered" and msg.get("content"):
                    saved_rating = st.session_state.feedback_saved.get(idx)
                    fb_col1, fb_col2, fb_col3 = st.columns([0.14, 0.16, 0.70])
                    if fb_col1.button("👍 Helpful", key=f"fb_up_{idx}", width="stretch"):
                        saved = submit_feedback(api_url, {
                            "question": msg.get("question", ""),
                            "answer": msg.get("content", ""),
                            "endpoint": ep,
                            "rating": "up",
                            "citations_count": len(msg.get("citations", [])),
                            "thread_id": msg.get("thread_id"),
                        })
                        st.session_state.feedback_saved[idx] = f"Saved 👍 (#{saved.get('id', '?')})"
                        st.rerun()
                    if fb_col2.button("👎 Needs work", key=f"fb_down_{idx}", width="stretch"):
                        saved = submit_feedback(api_url, {
                            "question": msg.get("question", ""),
                            "answer": msg.get("content", ""),
                            "endpoint": ep,
                            "rating": "down",
                            "citations_count": len(msg.get("citations", [])),
                            "thread_id": msg.get("thread_id"),
                        })
                        st.session_state.feedback_saved[idx] = f"Saved 👎 (#{saved.get('id', '?')})"
                        st.rerun()
                    if saved_rating:
                        fb_col3.caption(saved_rating)

        prompt = st.chat_input("Ask ScholarSetu about Maharashtra engineering scholarships...")
        if prompt:
            with st.spinner("Searching official scholarship sources..."):
                handle_question(prompt, api_url, mode, records)
            st.rerun()

    with tab_stacking:
        view_options = ["Eligible for my profile", "Matched from last chat", "Pick schemes manually"]
        stacking_view = st.radio(
            "Results table source",
            options=view_options,
            index=0,
            horizontal=True,
        )

        if stacking_view == "Eligible for my profile":
            selected_records = filter_eligible_records(
                records,
                category=category,
                gender=gender,
                family_income=int(family_income),
                has_disability=has_disability,
                is_hosteller=is_hosteller,
                include_abroad=include_abroad,
            )
        elif stacking_view == "Matched from last chat":
            selected_records = [
                records_by_id[rid]
                for rid in st.session_state.last_matched_ids
                if rid in records_by_id
            ]
        else:
            all_names = [r["scheme_name"] for r in records]
            default_picks = all_names[:2] + ([all_names[-1]] if len(all_names) >= 3 else [])
            picked_names = st.multiselect(
                "Select schemes to check stacking rules",
                options=all_names,
                default=default_picks,
            )
            selected_records = [r for r in records if r["scheme_name"] in picked_names]

        analysis = analyze_stacking(
            selected_records,
            annual_fee=int(annual_fee),
            gender=gender,
            is_hosteller=is_hosteller,
            city_tier=city_tier,
        )
        render_stacking_panel(analysis)


if __name__ == "__main__":
    main()
