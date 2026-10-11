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
- Wrappers also check the LLM's arguments (category spelling, positive amounts) before
  calling teammates' code, and always ask for the CURRENT month's data.

How the LLM sees a tool:
- Function name        -> the tool's name
- Docstring            -> when/why to use it (write these carefully, the LLM reads them!)
- Type-hinted inputs   -> the arguments the LLM must fill in
"""

from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool

from analytics.analytics import get_summary_metrics
from tools.budget_tool import (
    calculate_budget_status,
    get_all_budget_statuses,
    suggest_discretionary_reallocation,
)
from tools.categorization_tool import categorize_expense
from tools.database_tool import add_transaction, get_profile, get_transactions
from tools.ocr_tool import extract_receipt
from tools.spike_detector import detect_all_category_spikes, detect_spending_spike
from utils.helpers import CATEGORIES, normalize_date, to_iso_date

# ------------------------------------------------------------------------------
# Receipt hand-off
# An image can't be passed through the LLM as a text argument, so the UI hands the
# uploaded file to `run_agent()`, which stores it here. The `read_uploaded_receipt`
# tool then picks it up. A ContextVar keeps each Streamlit session's receipt separate.
# ------------------------------------------------------------------------------
current_receipt: ContextVar[Any] = ContextVar("current_receipt", default=None)


# ------------------------------------------------------------------------------
# Argument checks (the LLM may write "food", "groceries", -300 ...)
# ------------------------------------------------------------------------------
def _match_category(category: Optional[str]) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """Return (official category name, None) or (None, error for the LLM)."""
    wanted = (category or "").strip().lower()
    for official in CATEGORIES:
        if official.lower() == wanted:
            return official, None
    return None, {
        "error": f"Unknown category '{category}'. Use one of: {', '.join(CATEGORIES)}. "
        "If unsure, call suggest_category first."
    }


# ==============================================================================
# READ-ONLY TOOLS (look up data, never change anything)
# ==============================================================================
@tool
def get_budget_status(category: str) -> Dict[str, Any]:
    """Get this month's budget, amount spent, remaining amount, % used and status
    (UNDER BUDGET / NEAR LIMIT / OVER BUDGET / NO BUDGET SET) for ONE category.
    Use for questions like "how much food budget is left?" or "how much did I spend on transport?".
    `category` must be one of: Food, Transport, Shopping, Entertainment, Bills, Healthcare, Education, Others."""
    official, error = _match_category(category)
    if error:
        return error
    return calculate_budget_status(official)


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
def get_my_profile() -> Dict[str, Any]:
    """Get the user's monthly income, savings goal, usual monthly spending per category, and
    how much money is left this month after spending (income - spent so far).
    Use for "how much can I still save?", "am I on track for my savings goal?",
    "what is my income?"."""
    summary = get_summary_metrics()
    if summary["monthly_income"] is None:
        return {"error": "The user hasn't entered their income yet. Ask them to fill in the 'My Profile' page."}
    profile = get_profile()
    return {
        "monthly_income": summary["monthly_income"],
        "savings_goal": summary["savings_goal"],
        "spent_this_month": summary["total_spent"],
        "left_after_spending": summary["saved_so_far"],
        "savings_goal_on_track": summary["savings_on_track"],
        "usual_spending": profile["usual_spending"],
    }


@tool
def check_spending_spike(category: str) -> Dict[str, Any]:
    """Compare this week's spending with last week's for ONE category and report whether
    there is an unusual spike (amounts and % increase)."""
    official, error = _match_category(category)
    if error:
        return error
    return detect_spending_spike(official)


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
    if category:
        category, error = _match_category(category)
        if error:
            return [error]
    rows = get_transactions(category=category, merchant_query=merchant)
    rows.sort(key=lambda row: (to_iso_date(row["date"]), row["id"]), reverse=True)  # newest date first
    return rows[: max(1, min(limit, 50))]


@tool
def check_affordability(category: str, amount: float) -> Dict[str, Any]:
    """Check whether a NEW planned expense of `amount` rupees in `category` fits within
    the remaining budget. Returns the current remaining budget and what would be left after.
    Use for "can I afford ₹500 on food?" or "is 500 rs on pizza ok?"."""
    official, error = _match_category(category)
    if error:
        return error
    if amount <= 0:
        return {"error": "Amount must be greater than 0."}
    # Simple deterministic maths so the LLM never has to calculate.
    # (Could move into tools/budget_tool.py later — ask Member 3.)
    status = calculate_budget_status(official)
    if status["status"] == "NO BUDGET SET":
        return {
            "category": status["category"],
            "planned_amount": amount,
            "budget": 0.0,
            "spent_this_month": status["spent"],
            "no_budget_set": True,
            "can_afford": None,
            "note": "No budget is set for this category, so affordability can't be judged. "
            "Suggest setting one on the Budget page.",
        }
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
    `date` is DD-MM-YYYY (leave empty for today). `source` is "Text" or "Receipt".
    The result already includes the category's UPDATED budget status (`budget_after_saving`),
    so there is no need to call get_budget_status afterwards."""
    official, error = _match_category(category)
    if error:
        return {**error, "saved": False}
    if amount <= 0:
        return {"error": "Amount must be greater than 0. Ask the user for the correct amount.", "saved": False}
    if date:
        date = normalize_date(date)
        try:
            datetime.strptime(date, "%d-%m-%Y")
        except ValueError:
            return {"error": f"Could not read date '{date}'. Use DD-MM-YYYY (today is in your instructions).", "saved": False}

    saved = add_transaction(
        {
            "merchant": merchant,
            "amount": amount,
            "category": official,
            "date": date or "",
            "description": description,
            "source": source,
        }
    )
    return {
        "saved": True,
        "transaction": saved,
        "budget_after_saving": calculate_budget_status(official),
    }


@tool
def read_uploaded_receipt() -> Dict[str, Any]:
    """Read the receipt image the user uploaded with this message (OCR) and return
    merchant, date, items, tax, total and suggested category. Does NOT save it —
    call `add_expense` afterwards if the user wants it added."""
    receipt = current_receipt.get()
    if receipt is None:
        return {"error": "No receipt image was uploaded with this message."}
    result = extract_receipt(receipt)
    if not result["read_ok"]:
        return {
            "error": "The receipt image could not be read. Don't guess: ask the user to type "
            "the merchant and amount, or to try a clearer photo."
        }
    return result


# ------------------------------------------------------------------------------
# The list handed to the LLM (`llm.bind_tools(ALL_TOOLS)`) and to LangGraph's ToolNode.
# Add a new tool above, then add it here.
# ------------------------------------------------------------------------------
ALL_TOOLS = [
    get_budget_status,
    get_all_budgets_overview,
    get_monthly_summary,
    get_saving_suggestions,
    get_my_profile,
    check_spending_spike,
    check_all_spending_spikes,
    search_transactions,
    check_affordability,
    suggest_category,
    add_expense,
    read_uploaded_receipt,
]
