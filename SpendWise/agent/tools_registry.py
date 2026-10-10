"""
SpendWise — Agent Tool Registry
===============================
Owner: Member 1 (AI Agent / LangGraph)

Responsibility:
- Turns teammates' normal Python functions into LangChain *tools* the LLM can request.
- Each tool here is only a thin wrapper: a name + a description (docstring) + typed inputs.
  The real logic stays in `tools/`, `analytics/` and `database/` (owned by Members 2, 3, 4).
- The LLM never runs these functions itself. It only *requests* one (name + arguments);
  LangGraph's ToolNode in `agent/graph.py` executes it and sends the result back.

How the LLM sees a tool:
- Function name        -> the tool's name
- Docstring            -> when/why to use it (write these carefully, the LLM reads them!)
- Type-hinted inputs   -> the arguments the LLM must fill in
"""

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from analytics.analytics import get_summary_metrics
from tools.budget_tool import (
    calculate_budget_status,
    get_all_budget_statuses,
    suggest_discretionary_reallocation,
)
from tools.categorization_tool import categorize_expense
from tools.database_tool import add_transaction, get_transactions
from tools.ocr_tool import extract_receipt
from tools.spike_detector import detect_all_category_spikes, detect_spending_spike

# ------------------------------------------------------------------------------
# Receipt hand-off
# An image can't be passed through the LLM as a text argument, so the UI hands the
# uploaded file to `run_agent()`, which stores it here. The `read_uploaded_receipt`
# tool then picks it up. (Fine for a single-user local app.)
# ------------------------------------------------------------------------------
_current_receipt: Any = None


def set_current_receipt(receipt_file: Any) -> None:
    """Called by `agent/graph.py` before each run with the uploaded image (or None)."""
    global _current_receipt
    _current_receipt = receipt_file


# ==============================================================================
# READ-ONLY TOOLS (look up data, never change anything)
# ==============================================================================
@tool
def get_budget_status(category: str) -> Dict[str, Any]:
    """Get this month's budget, amount spent, remaining amount, % used and status
    (UNDER BUDGET / NEAR LIMIT / OVER BUDGET) for ONE category.
    Use for questions like "how much food budget is left?" or "how much did I spend on transport?".
    `category` must be one of: Food, Transport, Shopping, Entertainment, Bills, Healthcare, Education, Others."""
    return calculate_budget_status(category)


@tool
def get_all_budgets_overview() -> List[Dict[str, Any]]:
    """Get budget vs spending status for ALL 8 categories this month.
    Use to find which categories are over budget, or to explain why a budget alert was raised."""
    return get_all_budget_statuses()


@tool
def get_monthly_summary() -> Dict[str, Any]:
    """Get the overall picture for this month: total spent, total monthly budget,
    remaining budget and number of active alerts. Use for general "how am I doing?" questions."""
    return get_summary_metrics()


@tool
def get_saving_suggestions() -> Dict[str, Any]:
    """Find categories that are OVER budget and discretionary categories that still have
    unused budget, with ready-made suggestions on where to cut back.
    Use for "where can I reduce spending?" or "how do I fix my shopping overspend?"."""
    return suggest_discretionary_reallocation()


@tool
def check_spending_spike(category: str) -> Dict[str, Any]:
    """Compare this week's spending with last week's for ONE category and report whether
    there is an unusual spike (amounts and % increase)."""
    return detect_spending_spike(category)


@tool
def check_all_spending_spikes() -> List[Dict[str, Any]]:
    """Compare this week vs last week for ALL categories, biggest increases first.
    Use for "which category increased the most?" or "any unusual spending?"."""
    return detect_all_category_spikes()


@tool
def search_transactions(
    category: Optional[str] = None,
    merchant: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """List recent individual transactions (newest first), optionally filtered by category
    and/or merchant name (partial match, e.g. "swiggy"). Use to show which purchases
    caused an overspend, or to answer "what did I buy at Amazon?"."""
    rows = get_transactions(category=category, merchant_query=merchant)
    return rows[: max(1, min(limit, 50))]


@tool
def check_affordability(category: str, amount: float) -> Dict[str, Any]:
    """Check whether a NEW planned expense of `amount` rupees in `category` fits within
    the remaining budget. Returns the current remaining budget and what would be left after.
    Use for "can I afford ₹500 on food?" or "is 500 rs on pizza ok?"."""
    # Simple deterministic maths so the LLM never has to calculate.
    # (Could move into tools/budget_tool.py later — ask Member 3.)
    status = calculate_budget_status(category)
    left_after = round(status["remaining"] - amount, 2)
    return {
        "category": status["category"],
        "planned_amount": amount,
        "remaining_now": status["remaining"],
        "remaining_after": left_after,
        "can_afford": left_after >= 0,
        "budget": status["budget"],
        "status_now": status["status"],
    }


@tool
def suggest_category(merchant: str, description: str = "") -> str:
    """Suggest the best category for a merchant/description, e.g. "Swiggy" -> Food,
    "Uber" -> Transport. Use when the user didn't say the category."""
    return categorize_expense(merchant, description)


# ==============================================================================
# ACTION TOOLS (change data — only use when the user asks to add/log something)
# ==============================================================================
@tool
def add_expense(
    merchant: str,
    amount: float,
    category: str,
    date: Optional[str] = None,
    description: str = "",
    source: str = "Text",
) -> Dict[str, Any]:
    """SAVE a new expense to the database. Only call this when the user clearly asks to
    add/log/record an expense (or a receipt was read and they want it added).
    `category` must be one of: Food, Transport, Shopping, Entertainment, Bills, Healthcare, Education, Others.
    `date` is DD-MM-YYYY (leave empty for today). `source` is "Text" or "Receipt"."""
    return add_transaction(
        {
            "merchant": merchant,
            "amount": amount,
            "category": category,
            "date": date or "",
            "description": description,
            "source": source,
        }
    )


@tool
def read_uploaded_receipt() -> Dict[str, Any]:
    """Read the receipt image the user uploaded with this message (OCR) and return
    merchant, date, items, tax, total and suggested category. Does NOT save it —
    call `add_expense` afterwards if the user wants it added."""
    if _current_receipt is None:
        return {"error": "No receipt image was uploaded with this message."}
    return extract_receipt(_current_receipt)


# ------------------------------------------------------------------------------
# The list handed to the LLM (`llm.bind_tools(ALL_TOOLS)`) and to LangGraph's ToolNode.
# Add a new tool above, then add it here.
# ------------------------------------------------------------------------------
ALL_TOOLS = [
    get_budget_status,
    get_all_budgets_overview,
    get_monthly_summary,
    get_saving_suggestions,
    check_spending_spike,
    check_all_spending_spikes,
    search_transactions,
    check_affordability,
    suggest_category,
    add_expense,
    read_uploaded_receipt,
]
