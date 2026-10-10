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
- If Gemini is unavailable (no API key, no internet, quota) before any tool has run,
  falls back to the keyword-based demo agent in `agent/fallback_agent.py`.

Public interface (used by `pages/assistant.py`):
    run_agent(user_query, uploaded_receipt=None, chat_history=None) -> dict
    `chat_history` gives the agent short-term memory of the current chat.
"""

import json
import logging
import os
import time
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from agent import memory
from agent.fallback_agent import run_fallback_agent

# The real agent needs LangChain + LangGraph. If they aren't installed, the app still
# runs using the fallback agent (see `run_agent`).
try:
    from dotenv import dotenv_values
    from langchain_core.exceptions import ModelRateLimitError
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
    from langgraph.errors import GraphRecursionError
    from langgraph.graph import END, START, StateGraph
    from langgraph.prebuilt import ToolNode

    from agent.prompts import ORCHESTRATOR_SYSTEM_PROMPT
    from agent.state import AgentState
    from agent.tools_registry import ALL_TOOLS, current_receipt

    AGENT_LIBRARIES_AVAILABLE = True
except ImportError as import_error:  # pragma: no cover - depends on the environment
    AGENT_LIBRARIES_AVAILABLE = False
    _IMPORT_ERROR = import_error

logger = logging.getLogger(__name__)

ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
DEFAULT_MODEL = "gemini-3.8-flash"
# Safety net: stop if the agent <-> tools loop runs more than this many steps.
MAX_GRAPH_STEPS = 12
# Short-term memory: how many earlier chat messages Gemini sees (fewer = less data sent to Google).
MAX_HISTORY_MESSAGES = 6
# On a rate-limit error (free tier: 5 requests/minute), wait this long and retry once.
RATE_LIMIT_WAIT_SECONDS = 15


class LLMUnavailableError(Exception):
    """Gemini could not be reached (network, quota, wrong model, bad key ...)."""


# ==============================================================================
# 1. THE LLM (Gemini with our tools attached)
# ==============================================================================
def _setting(name: str, default: str = "") -> str:
    """Read a setting from real environment variables, else from SpendWise/.env.
    Editing .env takes effect without restarting the app."""
    value = os.getenv(name) or _env_file_values(ENV_FILE_PATH, _modified_time(ENV_FILE_PATH)).get(name) or default
    return value.strip()


def _modified_time(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


@lru_cache(maxsize=2)
def _env_file_values(path: str, modified_time: float) -> Dict[str, Optional[str]]:
    """Parse .env once per version of the file (a new modified time = re-read)."""
    return dotenv_values(path)


def _get_llm_with_tools():
    """
    Return Gemini with our tool list attached (`bind_tools`), so Gemini knows each
    tool's name, description and inputs. Returns None if no API key is set.
    """
    api_key = _setting("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return None
    return _build_llm(api_key, _setting("GEMINI_MODEL", DEFAULT_MODEL))


@lru_cache(maxsize=4)
def _build_llm(api_key: str, model: str):
    """Create the model once per (key, model) pair and reuse it."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0,  # 0 = most consistent answers, best for finance
    )
    return llm.bind_tools(ALL_TOOLS)


# ==============================================================================
# 2. THE GRAPH (nodes + edges)
# ==============================================================================
def agent_node(state: "AgentState") -> "AgentState":
    """
    NODE "agent": send the conversation so far to Gemini.
    Gemini replies EITHER with tool request(s) OR with the final answer text.
    """
    llm = _get_llm_with_tools()
    if llm is None:
        raise LLMUnavailableError("GEMINI_API_KEY is not set")
    for attempt in (1, 2):
        try:
            return {"messages": [llm.invoke(state["messages"])]}
        except ModelRateLimitError as exc:
            # Free tier = 5 requests/minute. Wait once and retry before giving up.
            if attempt == 2:
                raise LLMUnavailableError(type(exc).__name__) from exc
            time.sleep(RATE_LIMIT_WAIT_SECONDS)
        except Exception as exc:  # only errors from talking to Gemini are treated as "unavailable"
            raise LLMUnavailableError(type(exc).__name__) from exc


def route_after_agent(state: "AgentState") -> str:
    """
    CONDITIONAL EDGE: look at Gemini's latest reply.
    Did it request a tool? -> go to "tools". Otherwise -> END (it answered).
    """
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


def tool_error_message(error: Exception) -> str:
    """If a tool crashes, give Gemini an error result to explain, instead of crashing the page."""
    return f"Error: this tool failed ({type(error).__name__}: {error}). Tell the user it didn't work; don't guess the numbers."


@lru_cache(maxsize=1)
def build_spendwise_graph():
    """Draw the flowchart once and compile it into a runnable agent."""
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)            # Gemini thinks / decides
    graph.add_node("tools", ToolNode(ALL_TOOLS, handle_tool_errors=tool_error_message))  # runs the requested Python tools

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route_after_agent, ["tools", END])
    graph.add_edge("tools", "agent")               # results go back to Gemini (the loop)

    return graph.compile()


# ==============================================================================
# 3. PUBLIC ENTRY POINT
# ==============================================================================
def run_agent(
    user_query: str,
    uploaded_receipt: Any = None,
    chat_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Called by `pages/assistant.py`.

    Short-term memory: the agent remembers this chat by itself (`agent/memory.py`), so
    follow-ups like "yes, log it" make sense. `chat_history` (optional) lets a caller
    pass its own history instead: [{"role": "user" | "assistant", "content": str, ...}].

    Returns the dict described in `_answer`.
    """
    history = chat_history if chat_history is not None else memory.recent_messages()
    result = _answer(user_query, uploaded_receipt, history)
    memory.remember(user_query, result["response"])
    return result


def _answer(user_query: str, uploaded_receipt: Any, chat_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Runs the Gemini agent (or the fallback) for one question and returns:
        {
            "response": str,              final answer (Markdown)
            "mode": "llm" | "fallback",
            "intent": str,
            "selected_tools": list[str],  tools Gemini chose, in order
            "reasoning_trace": list[{"step": str, "detail": str}],
            "tool_outputs": dict,         raw tool results (for debugging / UI)
        }
    """
    if not AGENT_LIBRARIES_AVAILABLE:
        return _run_fallback(user_query, uploaded_receipt, reason=f"agent libraries are not installed ({_IMPORT_ERROR.name})")
    if _get_llm_with_tools() is None:
        return _run_fallback(user_query, uploaded_receipt, reason="GEMINI_API_KEY is not set in SpendWise/.env")

    question = user_query
    if uploaded_receipt is not None:
        question += "\n\n[The user attached a receipt image with this message.]"

    initial_state: AgentState = {
        "user_query": user_query,
        "messages": [
            SystemMessage(ORCHESTRATOR_SYSTEM_PROMPT.format(today=datetime.now().strftime("%d %B %Y"))),
            *_history_messages(chat_history, user_query),
            HumanMessage(question),
        ],
    }
    run_config = {
        "recursion_limit": MAX_GRAPH_STEPS,
        "max_concurrency": 1,  # run requested tools one after another, never at the same time
    }

    latest_state: Dict[str, Any] = initial_state
    failure: Optional[str] = None
    receipt_token = current_receipt.set(uploaded_receipt)
    try:
        # stream() hands us the state after every step, so if Gemini fails halfway
        # we still know which tools already ran.
        for latest_state in build_spendwise_graph().stream(initial_state, run_config, stream_mode="values"):
            pass
    except LLMUnavailableError as exc:
        failure = f"Gemini is unavailable right now ({exc})"
    except GraphRecursionError:
        failure = "the agent needed too many steps for this request"
    finally:
        current_receipt.reset(receipt_token)

    messages: List[BaseMessage] = latest_state["messages"]
    # Trace only what happened for THIS question (skip system rules, chat history, question).
    trace, selected_tools, tool_outputs = _build_trace(messages[len(initial_state["messages"]):])

    if failure:
        logger.warning("Agent stopped early: %s", failure)
        saved_something = any(
            isinstance(output, dict) and output.get("saved") is True for output in tool_outputs.values()
        )
        if not saved_something:
            # Nothing was saved yet, so the fallback can safely handle the whole request.
            return _run_fallback(user_query, uploaded_receipt, reason=failure)
        # An expense was already saved: re-running the request would save it twice.
        return {
            "response": _partial_answer(failure),
            "mode": "llm_partial",
            "intent": "PLANNED_BY_LLM",
            "selected_tools": selected_tools,
            "reasoning_trace": trace,
            "tool_outputs": tool_outputs,
        }

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


def _partial_answer(failure: str) -> str:
    """Explain a run that stopped after saving data, without repeating it."""
    return (
        f"> ⚠️ I started working on this, but {failure}, so I couldn't finish my answer.\n"
        "> ✅ Your expense **was saved** — please don't add it again. "
        "Open the trace below or the Transactions page to check it.\n\n"
        "Ask me about your budget again in a minute."
    )


def _history_messages(chat_history: Optional[List[Dict[str, Any]]], user_query: str) -> List["BaseMessage"]:
    """Turn the Assistant page's chat history into messages Gemini understands."""
    earlier = list(chat_history or [])
    if earlier and earlier[-1].get("role") == "user" and earlier[-1].get("content") == user_query:
        earlier.pop()  # the page already added the current question; it's sent separately
    messages: List[BaseMessage] = []
    for entry in earlier[-MAX_HISTORY_MESSAGES:]:
        if entry.get("role") == "user":
            messages.append(HumanMessage(entry["content"]))
        elif entry.get("role") == "assistant":
            messages.append(AIMessage(entry["content"]))
    return messages


def _message_text(message: "BaseMessage") -> str:
    """Gemini may return text as a plain string or as a list of parts; join the text parts."""
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)


def _short(value: Any, limit: int = 300) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + " …"


def _build_trace(messages: List["BaseMessage"]) -> Tuple[List[Dict[str, str]], List[str], Dict[str, Any]]:
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
