"""
SpendWise — Pandas Financial Analytics Engine
=============================================
Owner: Member 3 (Analytics + Budget + Alerts)

Responsibility:
- Performs all Pandas DataFrame aggregations for the Home Dashboard and Analytics Page:
  1. Summary KPIs (Total Spent, Monthly Budget, Remaining Budget, Active Alerts)
  2. Category-wise spending breakdown
  3. Budget vs Actual comparison DataFrame
  4. Weekly spending comparison
  5. Monthly spending summary
  6. Daily spending trend lines
- Keeps all calculation logic strictly out of `pages/*.py`.
"""

from __future__ import annotations
from typing import Any, Dict, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None  # type: ignore
    PANDAS_AVAILABLE = False

from tools.database_tool import get_transactions_df
from tools.budget_tool import get_all_budget_statuses, suggest_discretionary_reallocation
from tools.spike_detector import detect_all_category_spikes
from utils.helpers import CATEGORIES, resolve_period


def get_summary_metrics(month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Compute top-level dashboard KPI summary cards for the active month/year.
    """
    statuses = get_all_budget_statuses(month=month, year=year)
    total_budget = sum(item["budget"] for item in statuses)
    total_spent = sum(item["spent"] for item in statuses)
    remaining_budget = round(total_budget - total_spent, 2)

    over_budget_list = [item for item in statuses if item["status"] == "OVER BUDGET"]
    near_limit_list = [item for item in statuses if item["status"] == "NEAR LIMIT"]
    spikes = [s for s in detect_all_category_spikes() if s["spike_detected"]]

    return {
        "total_spent": round(total_spent, 2),
        "monthly_budget": round(total_budget, 2),
        "remaining_budget": remaining_budget,
        "budget_alerts_count": len(over_budget_list) + len(spikes),
        "over_budget_categories": over_budget_list,
        "near_limit_categories": near_limit_list,
        "detected_spikes": spikes,
    }


def get_budget_vs_actual_df(month: Optional[int] = None, year: Optional[int] = None) -> pd.DataFrame:
    """
    Return a Pandas DataFrame with columns:
    [Category, Budget, Spent, Remaining, Utilization_Pct, Status]
    """
    statuses = get_all_budget_statuses(month=month, year=year)
    df = pd.DataFrame(statuses)
    df.rename(
        columns={
            "category": "Category",
            "budget": "Budget",
            "spent": "Spent",
            "remaining": "Remaining",
            "utilization_pct": "Utilization_Pct",
            "status": "Status",
        },
        inplace=True,
    )
    return df


def get_category_spending_df(month: Optional[int] = None, year: Optional[int] = None) -> pd.DataFrame:
    """
    Return category-wise actual spending sorted descending for pie/bar visualizations.
    """
    df = get_budget_vs_actual_df(month=month, year=year)
    return df[["Category", "Spent", "Budget", "Status"]].sort_values(by="Spent", ascending=False)


def get_weekly_comparison_df() -> pd.DataFrame:
    """
    Return a DataFrame comparing Previous Week vs Current Week spending across categories.
    """
    spikes = detect_all_category_spikes()
    rows = []
    for item in spikes:
        rows.append(
            {
                "Category": item["category"],
                "Previous Week (₹)": item["previous_weekly_spending"],
                "Current Week (₹)": item["current_weekly_spending"],
                "Change (₹)": item["increase_amount"],
                "Change (%)": item["increase_pct"],
                "Spike Detected": item["spike_detected"],
            }
        )
    return pd.DataFrame(rows)


def get_monthly_spending_df() -> pd.DataFrame:
    """
    Aggregate total spending by Month-Year across the transaction history.
    """
    df = get_transactions_df()
    if df.empty:
        return pd.DataFrame(columns=["Month", "Total_Spent"])

    df["parsed_date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["Month_Sort"] = df["parsed_date"].dt.to_period("M")
    df["Month"] = df["parsed_date"].dt.strftime("%b %Y")

    grouped = (
        df.groupby(["Month_Sort", "Month"], as_index=False)["amount"]
        .sum()
        .sort_values("Month_Sort")
    )
    grouped.rename(columns={"amount": "Total_Spent"}, inplace=True)
    return grouped[["Month", "Total_Spent"]]


def get_spending_trends_df(month: Optional[int] = None, year: Optional[int] = None) -> pd.DataFrame:
    """
    Compute daily spending and cumulative monthly spending trend for the active month.
    """
    month, year = resolve_period(month, year)
    df = get_transactions_df()
    if df.empty:
        return pd.DataFrame(columns=["Date", "Daily_Spent", "Cumulative_Spent"])

    df["parsed_date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    mask = (df["parsed_date"].dt.month == month) & (df["parsed_date"].dt.year == year)
    month_df = df.loc[mask].copy()

    if month_df.empty:
        return pd.DataFrame(columns=["Date", "Daily_Spent", "Cumulative_Spent"])

    daily = (
        month_df.groupby("parsed_date", as_index=False)["amount"]
        .sum()
        .sort_values("parsed_date")
    )
    daily.rename(columns={"amount": "Daily_Spent"}, inplace=True)
    daily["Cumulative_Spent"] = daily["Daily_Spent"].cumsum()
    daily["Date"] = daily["parsed_date"].dt.strftime("%d %b")
    return daily[["Date", "Daily_Spent", "Cumulative_Spent"]]


def get_dashboard_ai_insights(month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
    """
    Combine budget overrun alerts, discretionary reallocation recommendations,
    and weekly spike detections into a structured insights dictionary for the UI.
    """
    reallocation = suggest_discretionary_reallocation(month=month, year=year)
    spikes = [s for s in detect_all_category_spikes() if s["spike_detected"]]

    return {
        "over_budget_alerts": reallocation["over_budget_categories"],
        "reallocation_suggestions": reallocation["suggestions"],
        "unused_discretionary": reallocation["unused_discretionary_categories"],
        "spending_spikes": spikes,
    }
