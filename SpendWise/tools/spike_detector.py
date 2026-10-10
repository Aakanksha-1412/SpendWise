"""
SpendWise — Spending Spike Detection Tool
=========================================
Owner: Member 3 (Analytics + Budget + Alerts)

Responsibility:
- Compares current weekly spending (Oct 1–Oct 8, 2026) against previous weekly
  spending (Sep 18–Sep 24, 2026) using Pandas.
- Flags categories where spending has spiked significantly (>= 35% increase and
  delta >= ₹300).
"""

from datetime import datetime
from typing import Dict, Any, List

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None  # type: ignore
    PANDAS_AVAILABLE = False

from tools.database_tool import get_transactions_df, get_transactions
from utils.helpers import CATEGORIES, format_inr


def detect_spending_spike(category: str, threshold_pct: float = 35.0) -> Dict[str, Any]:
    """
    Detect whether a specific category experienced an unusual spending spike
    in the current week compared with the previous week.

    Returns
    -------
    dict
        {
            "category": str,
            "previous_weekly_spending": float,
            "current_weekly_spending": float,
            "increase_amount": float,
            "increase_pct": float,
            "spike_detected": bool,
            "message": str
        }
    """
    if PANDAS_AVAILABLE:
        df = get_transactions_df()
        if df.empty:
            return {
                "category": category,
                "previous_weekly_spending": 0.0,
                "current_weekly_spending": 0.0,
                "increase_amount": 0.0,
                "increase_pct": 0.0,
                "spike_detected": False,
                "message": f"No transaction history available for {category}.",
            }

        df["parsed_date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
        cat_df = df[df["category"].str.lower() == category.strip().lower()]

        prev_mask = (cat_df["parsed_date"] >= "2026-09-18") & (cat_df["parsed_date"] <= "2026-09-30")
        curr_mask = (cat_df["parsed_date"] >= "2026-10-01") & (cat_df["parsed_date"] <= "2026-10-08")

        prev_spend = float(cat_df.loc[prev_mask, "amount"].sum())
        curr_spend = float(cat_df.loc[curr_mask, "amount"].sum())
    else:
        records = get_transactions()
        prev_spend = 0.0
        curr_spend = 0.0
        for r in records:
            if r["category"].strip().lower() == category.strip().lower():
                try:
                    dt = datetime.strptime(r["date"], "%d-%m-%Y")
                    iso = dt.strftime("%Y-%m-%d")
                    if "2026-09-18" <= iso <= "2026-09-30":
                        prev_spend += float(r["amount"])
                    elif "2026-10-01" <= iso <= "2026-10-08":
                        curr_spend += float(r["amount"])
                except ValueError:
                    continue
    diff = round(curr_spend - prev_spend, 2)

    if prev_spend > 0:
        pct_increase = round((diff / prev_spend) * 100.0, 1)
    else:
        pct_increase = 100.0 if curr_spend > 500 else 0.0

    spike_detected = (pct_increase >= threshold_pct) and (diff >= 300.0)

    if spike_detected:
        msg = (
            f"{category} spending has increased significantly (+{pct_increase}%) "
            f"from {format_inr(prev_spend)} in the previous week to {format_inr(curr_spend)} this week."
        )
    else:
        msg = f"{category} weekly spending is within normal historical variance ({format_inr(curr_spend)} vs {format_inr(prev_spend)} previously)."

    return {
        "category": category,
        "previous_weekly_spending": prev_spend,
        "current_weekly_spending": curr_spend,
        "increase_amount": diff,
        "increase_pct": pct_increase,
        "spike_detected": spike_detected,
        "message": msg,
    }


def detect_all_category_spikes(threshold_pct: float = 35.0) -> List[Dict[str, Any]]:
    """
    Run spending spike detection across all 8 official categories.
    """
    results = [detect_spending_spike(cat, threshold_pct=threshold_pct) for cat in CATEGORIES]
    # Sort so detected spikes appear first, ordered by largest increase amount
    results.sort(key=lambda r: (r["spike_detected"], r["increase_amount"]), reverse=True)
    return results
