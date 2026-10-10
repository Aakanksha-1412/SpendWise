"""
SpendWise — Agent Short-Term Memory
===================================
Owner: Member 1 (AI Agent / LangGraph)

Responsibility:
- Remembers the recent messages of the CURRENT chat, so follow-ups like
  "yes, log it" or "and transport?" make sense to Gemini.
- Inside the Streamlit app, every browser session gets its own memory
  (kept in `st.session_state`); refreshing the page starts a new chat.
- Outside Streamlit (tests, scripts) one shared in-process memory is used.

Only the chat TEXT is remembered, never old tool results, so Gemini must call
the tools again for up-to-date numbers.
"""

from typing import Dict, List

# How many messages are kept (questions + answers). `agent/graph.py` decides how many
# of these are actually sent to Gemini.
MAX_STORED_MESSAGES = 20
_SESSION_KEY = "spendwise_agent_memory"
_memory_outside_streamlit: List[Dict[str, str]] = []


def _store() -> List[Dict[str, str]]:
    """This chat's message list: per browser session in the app, shared otherwise."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx(suppress_warning=True) is not None:
            import streamlit as st

            return st.session_state.setdefault(_SESSION_KEY, [])
    except ImportError:
        pass
    return _memory_outside_streamlit


def recent_messages() -> List[Dict[str, str]]:
    """Earlier messages of this chat: [{"role": "user" | "assistant", "content": str}, ...]."""
    return list(_store())


def remember(question: str, answer: str) -> None:
    """Store one question and the agent's answer."""
    store = _store()
    store.append({"role": "user", "content": question})
    store.append({"role": "assistant", "content": answer})
    del store[:-MAX_STORED_MESSAGES]


def forget_all() -> None:
    """Start a new chat (e.g. for a "New chat" button)."""
    _store().clear()
