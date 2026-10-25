"""
SpendWise — My Profile & Money Plan Page
========================================
Owner: Member 4 (Streamlit UI + OCR)

Responsibility:
- First time: income, savings goal and the budget per category (saved as budgets).
  Later: only income and savings goal. Budgets are changed ONLY on the Budget page,
  so the same number is never entered in two places.
- After saving, shows the user's money plan: how income is split, what they can still
  spend while keeping the savings goal, and which budgets are fine / almost full / full.
- Optionally removes the current data ("start fresh").
- No SQL or calculations here: `tools/database_tool.py`, `tools/budget_tool.py` and
  `analytics/analytics.get_money_plan()` do the work; this page only draws it.
"""

import plotly.graph_objects as go
import streamlit as st

from analytics.analytics import get_money_plan
from tools.budget_tool import check_budgets_fit, suggest_budgets
from tools.database_tool import get_all_budgets, get_profile, get_transactions, remove_all_data, save_profile, upsert_budget
from utils.helpers import CATEGORIES, format_inr, period_label


def render_money_plan(plan: dict) -> None:
    st.markdown(f"### 💰 Your money plan for {period_label()}")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Monthly income", format_inr(plan["monthly_income"]))
    k2.metric("Savings goal", format_inr(plan["savings_goal"]))
    k3.metric("Spent so far", format_inr(plan["spent"]))
    k4.metric("You can still spend", format_inr(plan["can_still_spend"]))

    if plan["can_still_spend"] >= 0:
        st.success(
            f"You can still spend **{format_inr(plan['can_still_spend'])}** this month "
            f"and keep your **{format_inr(plan['savings_goal'])}** savings goal."
        )
    else:
        st.error(
            f"You've spent **{format_inr(-plan['can_still_spend'])}** more than income minus savings — "
            "this is coming out of your savings goal."
        )

    left, right = st.columns([1, 1.4], gap="large")
    with left:
        parts = [
            ("Spent so far", plan["spent"], "#DC2626"),
            ("Budget left", plan["budget_left"], "#0F766E"),
            ("Savings goal", plan["savings_goal"], "#16A34A"),
            ("Not planned yet", plan["unplanned"], "#94A3B8"),
        ]
        parts = [p for p in parts if p[1] > 0]
        donut = go.Figure(
            go.Pie(
                labels=[p[0] for p in parts],
                values=[p[1] for p in parts],
                marker_colors=[p[2] for p in parts],
                hole=0.55,
                sort=False,
            )
        )
        donut.update_layout(title="How your income is split", height=330, margin=dict(t=50, b=10, l=10, r=10))
        st.plotly_chart(donut, width="stretch")
    with right:
        rows = [row for row in plan["categories"] if row["budget"] > 0 or row["spent"] > 0]
        bars = go.Figure(
            [
                go.Bar(name="Budget", x=[r["category"] for r in rows], y=[r["budget"] for r in rows], marker_color="#CBD5E1"),
                go.Bar(
                    name="Spent",
                    x=[r["category"] for r in rows],
                    y=[r["spent"] for r in rows],
                    marker_color=["#DC2626" if r["status"] == "OVER BUDGET" else "#D97706" if r["status"] == "NEAR LIMIT" else "#0F766E" for r in rows],
                ),
            ]
        )
        bars.update_layout(barmode="group", title="Budget vs spent", height=330, margin=dict(t=50, b=10, l=10, r=10))
        st.plotly_chart(bars, width="stretch")

    st.markdown("#### Budget status")
    status_cols = st.columns(4)
    for idx, row in enumerate(plan["categories"]):
        with status_cols[idx % 4]:
            st.markdown(
                f"**{row['category']}** · {row['label']}  \n"
                f"{format_inr(row['spent'])} of {format_inr(row['budget'])}"
            )


def _income_and_savings_inputs(profile):
    c1, c2 = st.columns(2)
    with c1:
        income = st.number_input(
            "Monthly income / pocket money (₹)", min_value=0.0, step=500.0,
            value=float(profile["monthly_income"]) if profile else None, placeholder="e.g. 15000",
            key="profile_income",
        )
    with c2:
        savings_goal = st.number_input(
            "Savings goal per month (₹)", min_value=0.0, step=500.0,
            value=float(profile["savings_goal"]) if profile else None, placeholder="e.g. 2000",
            key="profile_savings",
        )
    return income or 0.0, savings_goal or 0.0


def _start_fresh_checkbox(default: bool) -> bool:
    if not get_transactions():
        return False
    return st.checkbox(
        "Start fresh: remove ALL my current expenses and budgets (e.g. demo data)",
        value=default, key="profile_start_fresh",
    )


def _valid(income: float, savings_goal: float) -> bool:
    if income <= 0:
        st.error("Please enter your monthly income (more than ₹0).")
        return False
    if savings_goal > income:
        st.error("Your savings goal can't be more than your income.")
        return False
    return True


def render_setup_form() -> None:
    """First time only: income, savings goal and the budgets themselves (saved as budgets)."""
    with st.form("setup_form"):
        st.markdown("##### 1. Income & savings")
        income, savings_goal = _income_and_savings_inputs(None)

        st.markdown(f"##### 2. Your monthly budget per category for {period_label()}")
        st.caption(
            "These become your budgets (change them any time on the 🎯 Budget page). "
            "Leave all empty and SpendWise splits your money automatically."
        )
        cols = st.columns(4)
        typed = {}
        for idx, cat in enumerate(CATEGORIES):
            with cols[idx % 4]:
                typed[cat] = st.number_input(
                    f"{cat} (₹)", min_value=0.0, step=100.0, value=None, placeholder="0",
                    key=f"setup_budget_{cat}",
                )
        start_fresh = _start_fresh_checkbox(default=True)
        submitted = st.form_submit_button("Save & create my budgets", type="primary")

    if submitted and _valid(income, savings_goal):
        if any(amount for amount in typed.values()):
            budgets = {cat: amount or 0.0 for cat, amount in typed.items()}
        else:
            budgets = suggest_budgets(income, savings_goal, {})
        too_much = check_budgets_fit(budgets, income, savings_goal)
        if too_much:
            st.error(too_much)
            return
        save_profile(income, savings_goal, {})  # profile first: demo data then never returns
        removed = remove_all_data() if start_fresh else 0
        for cat, amount in budgets.items():
            upsert_budget(cat, amount)
        message = f"Saved! Your {period_label()} budgets total {format_inr(sum(budgets.values()))}."
        if start_fresh:
            message += f" Removed {removed} old expenses."
        st.session_state["profile_saved_message"] = message
        st.rerun()


def render_edit_form(profile) -> None:
    """Later: only income and savings goal. Budgets are changed on the Budget page only."""
    with st.form("profile_form"):
        income, savings_goal = _income_and_savings_inputs(profile)
        st.caption("To change your budgets, use the 🎯 Budget page.")
        start_fresh = _start_fresh_checkbox(default=False)
        submitted = st.form_submit_button("Save", type="primary")

    if submitted and _valid(income, savings_goal):
        # "Start fresh" removes the budgets too, so then there is nothing that has to fit
        too_much = None if start_fresh else check_budgets_fit(get_all_budgets(), income, savings_goal)
        if too_much:
            st.error(f"{too_much} Lower your budgets on the 🎯 Budget page first.")
            return
        save_profile(income, savings_goal, profile["usual_spending"])
        message = "Saved!"
        if start_fresh:
            message += f" Removed {remove_all_data()} old expenses and your budgets — set new ones on the Budget page."
        st.session_state["profile_saved_message"] = message
        st.rerun()


def render_profile_page() -> None:
    saved_message = st.session_state.pop("profile_saved_message", None)
    if saved_message:
        st.success(saved_message)

    profile = get_profile()
    if profile is None:
        st.title("👋 Welcome! Let's set up your budget")
        st.caption(
            "Tell SpendWise about your money once — it's saved to your account. "
            f"Enter your income, savings goal and budgets for {period_label()}."
        )
        if get_transactions():
            st.info("You're looking at **demo data**. Fill this in and tick *Start fresh* to use only your own data.")
        render_setup_form()
        return

    st.title("👤 My Profile & Money Plan")
    render_money_plan(get_money_plan())
    st.divider()
    with st.expander("✏️ Edit income & savings goal"):
        render_edit_form(profile)
    if st.button("🎯 Open Budget page"):
        st.switch_page("pages/budget.py")


render_profile_page()
