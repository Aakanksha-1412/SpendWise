"""
SpendWise — My Profile & Setup Page
===================================
Owner: Member 4 (Streamlit UI + OCR)

Responsibility:
- Lets the user enter THEIR OWN numbers: monthly income, savings goal and what they
  usually spend per category in a month.
- Optionally removes the demo/sample data ("start fresh") so only real expenses are shown.
- Creates this month's budgets from the profile via `tools/budget_tool.suggest_budgets`.
- No SQL or budget maths here: everything goes through `tools/database_tool.py` and
  `tools/budget_tool.py`.
"""

import pandas as pd
import streamlit as st

from tools.budget_tool import suggest_budgets
from tools.database_tool import get_profile, get_transactions, remove_all_data, save_profile, upsert_budget
from utils.helpers import CATEGORIES, format_inr, period_label


def render_profile_page() -> None:
    st.title("👤 My Profile & Setup")
    st.caption(
        "Tell SpendWise about your money. Your income, savings goal and usual spending are used "
        f"to create your budgets for {period_label()} — instead of the demo numbers."
    )

    profile = get_profile()
    if profile is None and get_transactions():
        st.info(
            "You're currently looking at **demo data** (sample expenses and budgets). "
            "Fill in your details below and tick *Start fresh* to use only your own data."
        )

    saved_message = st.session_state.pop("profile_saved_message", None)
    if saved_message:
        st.success(saved_message)

    usual_now = profile["usual_spending"] if profile else {}
    with st.form("profile_form"):
        st.markdown("#### 1. Income & savings")
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

        st.markdown("#### 2. How much do you usually spend in a month? (rough guess is fine)")
        cols = st.columns(4)
        usual = {}
        for idx, cat in enumerate(CATEGORIES):
            with cols[idx % 4]:
                usual[cat] = st.number_input(
                    f"{cat} (₹)", min_value=0.0, step=100.0,
                    value=float(usual_now.get(cat, 0.0)), key=f"profile_usual_{cat}",
                )

        start_fresh = st.checkbox(
            "Start fresh: remove ALL current expenses and budgets (e.g. the demo data)",
            value=profile is None, key="profile_start_fresh",
        )
        submitted = st.form_submit_button("Save & create my budgets", type="primary")

    if submitted:
        if income <= 0:
            st.error("Please enter your monthly income (more than ₹0).")
        elif savings_goal > income:
            st.error("Your savings goal can't be more than your income.")
        else:
            save_profile(income, savings_goal, usual)  # profile first: demo data then never returns
            removed = remove_all_data() if start_fresh else 0
            budgets = suggest_budgets(income, savings_goal, usual)
            for cat, amount in budgets.items():
                upsert_budget(cat, amount)
            message = f"Saved! Your {period_label()} budgets total {format_inr(sum(budgets.values()))}."
            if start_fresh:
                message += f" Removed {removed} old expenses — only your own data from now on."
            st.session_state["profile_saved_message"] = message
            st.rerun()

    if profile:
        st.divider()
        st.markdown(f"#### Suggested budgets for {period_label()}")
        budgets = suggest_budgets(profile["monthly_income"], profile["savings_goal"], profile["usual_spending"])
        st.dataframe(
            pd.DataFrame(
                [
                    {"Category": cat, "Usual spending": format_inr(profile["usual_spending"][cat]), "Budget": format_inr(budgets[cat])}
                    for cat in CATEGORIES
                ]
            ),
            width="stretch",
            hide_index=True,
        )
        st.caption(
            f"Income {format_inr(profile['monthly_income'])} − savings goal {format_inr(profile['savings_goal'])} "
            f"= {format_inr(profile['monthly_income'] - profile['savings_goal'])} available to spend. "
            "If usual spending is more than that, Food/Shopping/Entertainment/Others are trimmed first. "
            "You can still change any budget on the Budget page."
        )
        if st.button("🎯 Open Budget page"):
            st.switch_page("pages/budget.py")


render_profile_page()
