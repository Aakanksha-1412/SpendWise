"""
SpendWise — My Profile & Money Plan Page
========================================
Owner: Member 4 (Streamlit UI + OCR)

Responsibility:
- Lets the user enter THEIR OWN numbers: monthly income, savings goal and what they
  usually spend per category in a month (saved per account, so it's entered only once).
- After saving, shows the user's money plan: how income is split, what they can still
  spend while keeping the savings goal, and which budgets are fine / almost full / full.
- Optionally removes the current data ("start fresh").
- No SQL or calculations here: `tools/database_tool.py`, `tools/budget_tool.py` and
  `analytics/analytics.get_money_plan()` do the work; this page only draws it.
"""

import plotly.graph_objects as go
import streamlit as st

from analytics.analytics import get_money_plan
from tools.budget_tool import suggest_budgets
from tools.database_tool import get_profile, get_transactions, remove_all_data, save_profile, upsert_budget
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


def render_profile_form(profile) -> None:
    usual_now = profile["usual_spending"] if profile else {}
    with st.form("profile_form"):
        st.markdown("##### 1. Income & savings")
        c1, c2 = st.columns(2)
        with c1:
            income = st.number_input(
                "Monthly income / pocket money (₹)", min_value=0.0, step=500.0,
                value=float(profile["monthly_income"]) if profile else 0.0, key="profile_income",
            )
        with c2:
            savings_goal = st.number_input(
                "Savings goal per month (₹)", min_value=0.0, step=500.0,
                value=float(profile["savings_goal"]) if profile else 0.0, key="profile_savings",
            )

        st.markdown("##### 2. How much do you usually spend in a month? (rough guess is fine)")
        cols = st.columns(4)
        usual = {}
        for idx, cat in enumerate(CATEGORIES):
            with cols[idx % 4]:
                usual[cat] = st.number_input(
                    f"{cat} (₹)", min_value=0.0, step=100.0,
                    value=float(usual_now.get(cat, 0.0)), key=f"profile_usual_{cat}",
                )

        update_budgets = st.checkbox(
            f"Set my {period_label()} budgets from this (you can still change them on the Budget page)",
            value=True, key="profile_update_budgets",
        )
        start_fresh = st.checkbox(
            "Start fresh: remove ALL my current expenses and budgets (e.g. demo data)",
            value=profile is None and bool(get_transactions()), key="profile_start_fresh",
        )
        submitted = st.form_submit_button("Save", type="primary")

    if submitted:
        if income <= 0:
            st.error("Please enter your monthly income (more than ₹0).")
        elif savings_goal > income:
            st.error("Your savings goal can't be more than your income.")
        else:
            save_profile(income, savings_goal, usual)
            removed = remove_all_data() if start_fresh else 0
            message = "Saved!"
            if update_budgets or start_fresh:
                budgets = suggest_budgets(income, savings_goal, usual)
                for cat, amount in budgets.items():
                    upsert_budget(cat, amount)
                message += f" Your {period_label()} budgets total {format_inr(sum(budgets.values()))}."
            if start_fresh:
                message += f" Removed {removed} old expenses."
            st.session_state["profile_saved_message"] = message
            st.rerun()


def render_profile_page() -> None:
    st.title("👤 My Profile & Money Plan")

    saved_message = st.session_state.pop("profile_saved_message", None)
    if saved_message:
        st.success(saved_message)

    profile = get_profile()
    if profile is None:
        st.caption(
            "Tell SpendWise about your money once — it's saved to your account. Your income, savings goal "
            f"and usual spending are used to create your budgets for {period_label()}."
        )
        if get_transactions():
            st.info("You're looking at **demo data**. Fill this in and tick *Start fresh* to use only your own data.")
        render_profile_form(None)
        return

    render_money_plan(get_money_plan())
    st.divider()
    with st.expander("✏️ Edit my details (income, savings goal, usual spending)"):
        render_profile_form(profile)
    if st.button("🎯 Open Budget page"):
        st.switch_page("pages/budget.py")


render_profile_page()
