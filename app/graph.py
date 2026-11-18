import uuid
from functools import lru_cache
from typing import Optional

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict

try:
    from langgraph.checkpoint.memory import InMemorySaver
except ImportError:  # older LangGraph versions call it MemorySaver
    from langgraph.checkpoint.memory import MemorySaver as InMemorySaver

from app.agent_loop import FINAL_ACTION, MAX_STEPS, STEP_LIMIT_TEXT, decide, run_tool

NEEDS_APPROVAL = {"compare_schemes"}  # tools that wait for a person's approval
MAX_HISTORY = 5                       # earlier turns remembered per conversation
OBSERVATION_IN_REPLY = 300            # a tool result is cut to this length in the API reply


class AgentNotFound(LookupError):
    """No conversation exists for this thread_id."""


class AgentConflict(ValueError):
    """The request does not fit the state of the conversation."""


class AgentState(TypedDict, total=False):
    question: str
    history: list             # earlier turns: [{"question": ..., "answer": ...}]
    scratch: list             # this turn's steps: [{"action", "input", "observation"}]
    pending: Optional[dict]   # the tool call the model chose, not yet run
    approved: bool
    answer: str
    steps: int


def start_node(state):
    """A new question starts: clear the per-turn fields (history is kept)."""
    return {"scratch": [], "pending": None, "approved": False, "answer": "", "steps": 0}


def plan_node(state):
    steps = state.get("steps", 0)
    if steps >= MAX_STEPS:
        return {"answer": STEP_LIMIT_TEXT, "pending": None}
    decision = decide(state["question"], state.get("history", []), state.get("scratch", []))
    if decision["action"] == FINAL_ACTION:
        return {"answer": decision["input"], "pending": None, "steps": steps + 1}
    return {"pending": {"action": decision["action"], "input": decision["input"]}, "steps": steps + 1}


def route_after_plan(state):
    pending = state.get("pending")
    if state.get("answer") or not pending:
        return "finish"
    return "approve" if pending["action"] in NEEDS_APPROVAL else "run_tool"


def approve_node(state):
    """Pause here. The graph resumes when a person sends approve true or false."""
    pending = state["pending"]
    decision = interrupt({
        "message": f"The agent wants to run '{pending['action']}'. Approve?",
        "action": pending["action"],
        "input": pending["input"],
    })
    approved = decision is True or (isinstance(decision, dict) and decision.get("approve") is True)
    if approved:
        return {"approved": True}
    rejected = {"action": pending["action"], "input": pending["input"],
                "observation": "The user did not approve this tool call, so it was not run."}
    return {"approved": False, "pending": None, "scratch": state.get("scratch", []) + [rejected]}


def route_after_approve(state):
    return "run_tool" if state.get("approved") else "plan"


def tool_node(state):
    pending = state["pending"]
    observation = run_tool(pending["action"], pending["input"])
    step = {"action": pending["action"], "input": pending["input"], "observation": observation}
    return {"scratch": state.get("scratch", []) + [step], "pending": None}


def finish_node(state):
    turn = {"question": state["question"], "answer": state["answer"]}
    return {"history": (state.get("history", []) + [turn])[-MAX_HISTORY:]}


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("start_turn", start_node)
    builder.add_node("plan", plan_node)
    builder.add_node("approve", approve_node)
    builder.add_node("run_tool", tool_node)
    builder.add_node("finish", finish_node)
    builder.add_edge(START, "start_turn")
    builder.add_edge("start_turn", "plan")
    builder.add_conditional_edges("plan", route_after_plan,
                                  {"finish": "finish", "approve": "approve", "run_tool": "run_tool"})
    builder.add_conditional_edges("approve", route_after_approve,
                                  {"run_tool": "run_tool", "plan": "plan"})
    builder.add_edge("run_tool", "plan")
    builder.add_edge("finish", END)
    return builder.compile(checkpointer=InMemorySaver())  # memory lives while the server runs


@lru_cache(maxsize=1)
def get_graph():
    return build_graph()


def config_for(thread_id):
    return {"configurable": {"thread_id": thread_id}}


def describe(thread_id, snapshot):
    """The state of a conversation as the API reply."""
    values = snapshot.values
    waiting = bool(snapshot.next)  # the graph is paused at the approval step
    scratch = values.get("scratch", [])
    return {
        "thread_id": thread_id,
        "status": "awaiting_approval" if waiting else "answered",
        "answer": None if waiting else values.get("answer", ""),
        "pending_action": values.get("pending") if waiting else None,
        "steps": [{"action": s["action"], "input": s["input"],
                   "observation": s["observation"][:OBSERVATION_IN_REPLY]} for s in scratch],
        "tools_used": [s["action"] for s in scratch],
        "turns": len(values.get("history", [])),
    }


def start_turn(question, thread_id=None):
    """Ask a question in a conversation (a new one if no thread_id is given).
    The reply is either the answer or a request for approval."""
    graph = get_graph()
    thread_id = thread_id or str(uuid.uuid4())
    config = config_for(thread_id)
    if graph.get_state(config).next:
        raise AgentConflict("This conversation is waiting for your approval. "
                            "Send approve true or false first.")
    graph.invoke({"question": question.strip()}, config)
    return describe(thread_id, graph.get_state(config))


def resume_turn(thread_id, approve):
    """Answer the approval request of a paused conversation."""
    graph = get_graph()
    config = config_for(thread_id)
    snapshot = graph.get_state(config)
    if not snapshot.values:
        raise AgentNotFound(f"No conversation with thread_id '{thread_id}'.")
    if not snapshot.next:
        raise AgentConflict("Nothing is waiting for approval in this conversation.")
    graph.invoke(Command(resume=bool(approve)), config)
    return describe(thread_id, graph.get_state(config))