"""
SpendWise — LangGraph Agent State Schema
========================================
Owner: Member 1 (AI Agent / LangGraph)

Responsibility:
- Defines the strongly-typed state (`AgentState`) passed between nodes in the
  SpendWise LangGraph orchestration graph (`agent/graph.py`).
"""

from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict, total=False):
    """
    State dictionary maintained across the SpendWise LangGraph execution cycle:

    START
      ↓
    understand_request     -> populates `intent`, `target_category`, `extracted_expense`
      ↓
    decide_required_tool   -> populates `selected_tools`
      ↓
    call_tool              -> populates `tool_outputs`
      ↓
    evaluate_result        -> populates `evaluation_notes`
      ↓
    generate_response      -> populates `final_response`
      ↓
    END
    """
    user_query: str
    uploaded_receipt: Optional[Any]
    intent: str
    target_category: Optional[str]
    extracted_expense: Optional[Dict[str, Any]]
    selected_tools: List[str]
    tool_outputs: Dict[str, Any]
    evaluation_notes: List[str]
    reasoning_trace: List[Dict[str, str]]
    final_response: str
