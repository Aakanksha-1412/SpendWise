"""
SpendWise — Budget Calculation & Discretionary Reallocation Tool
================================================================
Owner: Member 3 (Analytics + Budget + Alerts)

Responsibility:
- Deterministic Python/Pandas calculations comparing monthly category budgets
  against actual SQLite spending.
- Identifies `OVER BUDGET`, `NEAR LIMIT` (>=80%), `UNDER BUDGET` and `NO BUDGET SET` states.
- All functions default to the CURRENT month.
- Recommends specific discretionary categories with unused budget where the user
  can reduce spending when another category exceeds its monthly limit.
"""

import math
from typing import Any, Dict, List, Optional
from tools.database_tool import get_all_budgets, get_category_spending, get_spending_by_category
from utils.helpers import CATEGORIES, DISCRETIONARY_CATEGORIES, format_inr


def calculate_budget_status(category: str, month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Calculate budget vs actual spending status for a single category.

    Returns
    -------
    dict
        {
            "category": str,
            "budget": float,
            "spent": float,
            "remaining": float,
            "utilization_pct": float,
            "status": "OVER BUDGET" | "NEAR LIMIT" | "UNDER BUDGET" | "NO BUDGET SET"
        }
    """
    budgets = get_all_budgets(month=month, year=year)
    budget_amt = float(budgets.get(category, 0.0))
    spent_amt = float(get_category_spending(category, month=month, year=year))
    return _status(category, budget_amt, spent_amt)


def _status(category: str, budget_amt: float, spent_amt: float) -> Dict[str, Any]:
    """Budget status dict from a budget and an amount spent (shared by single + overview)."""
    remaining_amt = round(budget_amt - spent_amt, 2)
    utilization_pct = round((spent_amt / budget_amt * 100.0), 1) if budget_amt > 0 else 0.0

    if budget_amt <= 0:
        status = "NO BUDGET SET"  # nothing to compare against yet
    elif remaining_amt < 0:
        status = "OVER BUDGET"
    elif utilization_pct >= 80.0:
        status = "NEAR LIMIT"
    else:
        status = "UNDER BUDGET"

    return {
        "category": category,
        "budget": budget_amt,
        "spent": spent_amt,
        "remaining": remaining_amt,
        "utilization_pct": utilization_pct,
        "status": status,
    }


def get_all_budget_statuses(month: Optional[int] = None, year: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Return budget status dictionaries for all 8 official SpendWise categories
    (budgets and transactions are loaded once, not once per category).
    """
    budgets = get_all_budgets(month=month, year=year)
    spending = get_spending_by_category(month=month, year=year)
    return [_status(cat, float(budgets.get(cat, 0.0)), float(spending.get(cat, 0.0))) for cat in CATEGORIES]


def suggest_discretionary_reallocation(month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Analyze all category budgets and generate actionable suggestions on where
    to trim discretionary spending to offset categories that exceeded their budget.
    """
    statuses = get_all_budget_statuses(month=month, year=year)
    over_budget_cats = [s for s in statuses if s["status"] == "OVER BUDGET"]
    unused_discretionary = [
        s for s in statuses
        if s["category"] in DISCRETIONARY_CATEGORIES and s["remaining"] > 0
    ]
    unused_discretionary.sort(key=lambda x: x["remaining"], reverse=True)

    total_overrun = sum(abs(s["remaining"]) for s in over_budget_cats)
    total_discretionary_buffer = sum(s["remaining"] for s in unused_discretionary)

    suggestions: List[str] = []
    if over_budget_cats:
        for ob in over_budget_cats:
            overrun_str = format_inr(abs(ob["remaining"]))
            if unused_discretionary:
                top_buffers = ", ".join(
                    f"{u['category']} ({format_inr(u['remaining'])} left)"
                    for u in unused_discretionary[:3]
                )
                suggestions.append(
                    f"Your {ob['category']} expenses have exceeded your monthly budget by {overrun_str}. "
                    f"You still have unused discretionary budget in {top_buffers}. "
                    f"Consider freezing non-essential spending in those categories for the rest of the month."
                )
            else:
                suggestions.append(
                    f"Your {ob['category']} expenses have exceeded your monthly budget by {overrun_str}. "
                    f"All discretionary buffers are depleted—avoid non-essential purchases this month."
                )
    else:
        suggestions.append(
            "All categories are currently within their monthly budget limits. Keep tracking daily expenses to maintain your savings buffer."
        )

    return {
        "over_budget_categories": over_budget_cats,
        "unused_discretionary_categories": unused_discretionary,
        "total_overrun": total_overrun,
        "total_discretionary_buffer": total_discretionary_buffer,
        "suggestions": suggestions,
    }


# Starting shares used only when the user gave no usual spending at all
DEFAULT_BUDGET_SHARES: Dict[str, float] = {
    "Food": 5000, "Transport": 3000, "Shopping": 4000, "Entertainment": 2000,
    "Bills": 3500, "Healthcare": 1500, "Education": 4000, "Others": 1500,
}


def suggest_budgets(monthly_income: float, savings_goal: float, usual_spending: Dict[str, float]) -> Dict[str, float]:
    """
    Suggest a monthly budget per category from the user's profile.
    - Money available to spend = income - savings goal.
    - If usual spending fits, each budget = usual spending.
    - If it doesn't fit, discretionary "wants" (Food, Shopping, Entertainment, Others) are
      trimmed first; essentials (Bills, Transport, Healthcare, Education) only if still needed.
    - With no usual spending given, the available money is split using DEFAULT_BUDGET_SHARES.
    """
    available = max(float(monthly_income) - float(savings_goal), 0.0)
    usual = {cat: max(float(usual_spending.get(cat, 0.0) or 0.0), 0.0) for cat in CATEGORIES}
    total = sum(usual.values())

    if total == 0:
        weight_sum = sum(DEFAULT_BUDGET_SHARES.values())
        return {cat: float(math.floor(available * DEFAULT_BUDGET_SHARES[cat] / weight_sum / 50) * 50) for cat in CATEGORIES}
    if total <= available:
        return {cat: round(amount, 2) for cat, amount in usual.items()}

    overflow = total - available
    wants_total = sum(usual[cat] for cat in DISCRETIONARY_CATEGORIES)
    budgets = dict(usual)
    if wants_total >= overflow:
        factor = (wants_total - overflow) / wants_total
        for cat in DISCRETIONARY_CATEGORIES:
            budgets[cat] = float(math.floor(usual[cat] * factor))
    else:
        needs_total = total - wants_total
        factor = available / needs_total if needs_total else 0.0
        for cat in CATEGORIES:
            budgets[cat] = 0.0 if cat in DISCRETIONARY_CATEGORIES else float(math.floor(usual[cat] * factor))
    return budgets
