"""
SpendWise — LangGraph Agent (Gemini Orchestrator)
=================================================
Owner: Member 1 (AI Agent / LangGraph)

Responsibility:
- The "brain" of SpendWise. Gemini reads the user's request, DECIDES which tools to
  call, LangGraph RUNS those tools (plain Python / SQLite / Pandas), the results go back
  to Gemini, and the loop repeats until Gemini has enough information to answer.

        START
          ↓
       [agent]  Gemini: understand request + decide tool(s)   ◄──────┐
          ↓                                                         │
     tool requested?                                                │
       ├─ yes → [tools]  ToolNode runs the Python function(s) ──────┘  (evaluate & loop)
       └─ no  → END      Gemini's reply is the final answer

- LLM reasoning (Gemini) is kept separate from deterministic calculations (tools/).
- If Gemini is unavailable (no API key, no internet, quota), falls back to the
  keyword-based demo agent in `agent/fallback_agent.py` so the app still works.

Public interface (used by `pages/assistant.py`):
    run_agent(user_query, uploaded_receipt=None) -> dict
"""

import json
import logging
import os
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Tuple

from dotenv import dotenv_values
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from agent.fallback_agent import run_fallback_agent
from agent.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from agent.state import AgentState
from agent.tools_registry import ALL_TOOLS, set_current_receipt

logger = logging.getLogger(__name__)

# Read only the agent's settings from SpendWise/.env (real environment variables win).
_ENV_FILE = dotenv_values(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))


def _setting(name: str, default: str = "") -> str:
    return (os.getenv(name) or _ENV_FILE.get(name) or default).strip()


DEFAULT_MODEL = "gemini-3.8-flash"
# Safety net: stop if the agent <-> tools loop runs more than this many steps.
MAX_GRAPH_STEPS = 12


# ==============================================================================
# 1. THE LLM (Gemini with our tools attached)
# ==============================================================================
@lru_cache(maxsize=1)
def _get_llm_with_tools():
    """
    Create the Gemini chat model and attach (`bind_tools`) our tool list, so Gemini
    knows each tool's name, description and inputs. Returns None if no API key is set.
    """
    api_key = _setting("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return None

    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=_setting("GEMINI_MODEL", DEFAULT_MODEL),
        google_api_key=api_key,
        temperature=0,  # 0 = most consistent answers, best for finance
    )
    return llm.bind_tools(ALL_TOOLS)


# ==============================================================================
# 2. THE GRAPH (nodes + edges)
# ==============================================================================
def agent_node(state: AgentState) -> AgentState:
    """
    NODE "agent": send the conversation so far to Gemini.
    Gemini replies EITHER with tool request(s) OR with the final answer text.
    """
    reply = _get_llm_with_tools().invoke(state["messages"])
    return {"messages": [reply]}


def route_after_agent(state: AgentState) -> str:
    """
    CONDITIONAL EDGE: look at Gemini's latest reply.
    Did it request a tool? -> go to "tools". Otherwise -> END (it answered).
    """
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


@lru_cache(maxsize=1)
def build_spendwise_graph():
    """Draw the flowchart once and compile it into a runnable agent."""
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)            # Gemini thinks / decides
    graph.add_node("tools", ToolNode(ALL_TOOLS))   # LangGraph runs the requested Python tools

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, ["tools", END])
    graph.add_edge("tools", "agent")               # results go back to Gemini (the loop)

    return graph.compile()


# ==============================================================================
# 3. PUBLIC ENTRY POINT
# ==============================================================================
def run_agent(user_query: str, uploaded_receipt: Any = None) -> Dict[str, Any]:
    """
    Called by `pages/assistant.py`. Runs the Gemini agent and returns:
        {
            "response": str,              final answer (Markdown)
            "mode": "llm" | "fallback",
            "intent": str,
            "selected_tools": list[str],  tools Gemini chose, in order
            "reasoning_trace": list[{"step": str, "detail": str}],
            "tool_outputs": dict,         raw tool results (for debugging / UI)
        }
    """
    if _get_llm_with_tools() is None:
        return _run_fallback(user_query, uploaded_receipt, reason="GEMINI_API_KEY is not set in SpendWise/.env")

    question = user_query
    if uploaded_receipt is not None:
        question += "\n\n[The user attached a receipt image with this message.]"

    initial_state: AgentState = {
        "user_query": user_query,
        "messages": [
            SystemMessage(ORCHESTRATOR_SYSTEM_PROMPT.format(today=datetime.now().strftime("%d %B %Y"))),
            HumanMessage(question),
        ],
    }

    set_current_receipt(uploaded_receipt)
    try:
        final_state = build_spendwise_graph().invoke(initial_state, {"recursion_limit": MAX_GRAPH_STEPS})
    except Exception as exc:  # no internet, quota exceeded, wrong model name, endless loop ...
        logger.warning("Gemini agent failed, using fallback: %r", exc)
        return _run_fallback(user_query, uploaded_receipt, reason=f"Gemini is unavailable right now ({type(exc).__name__})")
    finally:
        set_current_receipt(None)

    messages: List[BaseMessage] = final_state["messages"]
    trace, selected_tools, tool_outputs = _build_trace(messages)

    return {
        "response": _message_text(messages[-1]) or "Sorry, I couldn't produce an answer. Please try rephrasing.",
        "mode": "llm",
        "intent": "PLANNED_BY_LLM",
        "selected_tools": selected_tools,
        "reasoning_trace": trace,
        "tool_outputs": tool_outputs,
    }


# ==============================================================================
# 4. HELPERS
# ==============================================================================
def _run_fallback(user_query: str, uploaded_receipt: Any, reason: str) -> Dict[str, Any]:
    """Use the keyword-based demo agent and clearly label the answer."""
    result = run_fallback_agent(user_query, uploaded_receipt)
    result["mode"] = "fallback"
    result["response"] = (
        f"> ⚠️ **Demo mode (no LLM):** {reason}. "
        f"This answer comes from simple keyword rules.\n\n{result['response']}"
    )
    return result


def _message_text(message: BaseMessage) -> str:
    """Gemini may return text as a plain string or as a list of parts; join the text parts."""
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)


def _short(value: Any, limit: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + " …"


def _build_trace(messages: List[BaseMessage]) -> Tuple[List[Dict[str, str]], List[str], Dict[str, Any]]:
    """
    Turn the message history into a readable step-by-step trace for the UI, showing
    what Gemini decided, what each tool returned, and when Gemini answered.
    """
    trace: List[Dict[str, str]] = []
    selected_tools: List[str] = []
    tool_outputs: Dict[str, Any] = {}

    for message in messages:
        if isinstance(message, AIMessage) and message.tool_calls:
            calls = []
            for call in message.tool_calls:
                selected_tools.append(call["name"])
                calls.append(f"`{call['name']}({_short(call['args'], 120)})`")
            trace.append({"step": f"{len(trace) + 1}. 🧠 Gemini decides", "detail": "Request tool(s): " + ", ".join(calls)})

        elif isinstance(message, ToolMessage):
            try:
                output = json.loads(message.content)
            except (TypeError, ValueError):
                output = message.content
            key = message.name if message.name not in tool_outputs else f"{message.name}_{len(tool_outputs)}"
            tool_outputs[key] = output
            trace.append({"step": f"{len(trace) + 1}. 🔧 Tool runs (Python)", "detail": f"`{message.name}` returned: {_short(output)}"})

        elif isinstance(message, AIMessage):
            detail = (
                "Evaluated the tool results and wrote the final answer."
                if selected_tools
                else "Answered directly — no tool was needed."
            )
            trace.append({"step": f"{len(trace) + 1}. ✍️ Gemini answers", "detail": detail})

    return trace, selected_tools, tool_outputs
