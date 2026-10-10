"""
SpendWise — LangGraph Agent State Schema
========================================
Owner: Member 1 (AI Agent / LangGraph)

Responsibility:
- Defines the shared "notebook" (`AgentState`) that every node in the agent graph
  reads from and writes to.
"""

from typing import Annotated, Any, Dict, List, Optional, TypedDict

try:
    from langgraph.graph.message import add_messages
except ImportError:  # keeps the offline fallback importable without langgraph
    def add_messages(left: list, right: list) -> list:
        return left + right


class AgentState(TypedDict, total=False):
    """
    Real Gemini agent (`agent/graph.py`) uses `messages`: the whole conversation for
    this request, which grows on every pass through the loop:

        System rules -> User question -> Gemini tool request -> Tool result
        -> Gemini tool request -> Tool result -> ... -> Gemini final answer

    `add_messages` tells LangGraph to APPEND each node's new messages to the list
    instead of replacing it.

    Offline fallback (`agent/fallback_agent.py`) uses the remaining fields, filled in order:
        user_query -> intent / target_category -> selected_tools
        -> tool_outputs -> evaluation_notes -> final_response
    """
    # Real agent (LangGraph + Gemini)
    messages: Annotated[List[Any], add_messages]

    # Shared
    user_query: str
    uploaded_receipt: Optional[Any]
    reasoning_trace: List[Dict[str, str]]
    final_response: str

    # Offline fallback only
    intent: str
    target_category: Optional[str]
    extracted_expense: Optional[Dict[str, Any]]
    selected_tools: List[str]
    tool_outputs: Dict[str, Any]
    evaluation_notes: List[str]
