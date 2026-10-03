"""
SpendWise — Budget Calculation & Discretionary Reallocation Tool
================================================================
Owner: Team Member 4 (Analytics + Budget + Spike Detection)

Responsibility:
- Deterministic Python/Pandas calculations comparing monthly category budgets
  against actual SQLite spending.
- Identifies `OVER BUDGET`, `NEAR LIMIT` (>=80%), and `UNDER BUDGET` states.
- Recommends specific discretionary categories with unused budget where the user
  can reduce spending when another category exceeds its monthly limit.
"""

from typing import Dict, Any, List
from tools.database_tool import get_all_budgets, get_category_spending
from utils.helpers import CATEGORIES, DISCRETIONARY_CATEGORIES, format_inr


def calculate_budget_status(category: str, month: int = 10, year: int = 2026) -> Dict[str, Any]:
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
            "status": "OVER BUDGET" | "NEAR LIMIT" | "UNDER BUDGET"
        }
    """
    budgets = get_all_budgets(month=month, year=year)
    budget_amt = float(budgets.get(category, 0.0))
    spent_amt = float(get_category_spending(category, month=month, year=year))
    remaining_amt = round(budget_amt - spent_amt, 2)
    utilization_pct = round((spent_amt / budget_amt * 100.0), 1) if budget_amt > 0 else 0.0

    if remaining_amt < 0:
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


def get_all_budget_statuses(month: int = 10, year: int = 2026) -> List[Dict[str, Any]]:
    """
    Return budget status dictionaries for all 8 official SpendWise categories.
    """
    return [calculate_budget_status(cat, month=month, year=year) for cat in CATEGORIES]


def suggest_discretionary_reallocation(month: int = 10, year: int = 2026) -> Dict[str, Any]:
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
