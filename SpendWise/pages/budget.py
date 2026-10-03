"""
SpendWise — Monthly Budget Manager Page
=======================================
Owner: UI / Frontend Team & Team Member 4 (Budget Tool Integration)

Responsibility:
- Allows the user to define and update monthly budgets for all 8 official categories:
  [Food, Transport, Shopping, Entertainment, Bills, Healthcare, Education, Others]
- Displays Budget, Spent, Remaining, and Status (`OVER BUDGET`, `NEAR LIMIT`, `UNDER BUDGET`).
- Calls `tools/budget_tool.py` and `tools/database_tool.py`.
"""

import streamlit as st
import pandas as pd

from tools.budget_tool import get_all_budget_statuses
from tools.database_tool import upsert_budget
from utils.helpers import CATEGORIES, format_inr


def render_budget_page() -> None:
    st.title("🎯 Monthly Budget Configuration")
    st.caption("Define category-wise monthly budgets for October 2026 and monitor real-time utilization.")

    statuses = get_all_budget_statuses(month=10, year=2026)

    # -------------------------------------------------------------------------
    # 1. UPDATE CATEGORY BUDGET FORM
    # -------------------------------------------------------------------------
    with st.expander("✏️ Update Category Monthly Budgets", expanded=False):
        with st.form("budget_update_form"):
            b_cols = st.columns(4)
            updated_values = {}
            for idx, item in enumerate(statuses):
                cat = item["category"]
                with b_cols[idx % 4]:
                    updated_values[cat] = st.number_input(
                        f"{cat} Budget (₹)",
                        min_value=0.0,
                        value=float(item["budget"]),
                        step=500.0,
                    )
            if st.form_submit_button("Save Monthly Budgets", type="primary"):
                for cat, val in updated_values.items():
                    upsert_budget(cat, val, month=10, year=2026)
                st.success("Updated monthly budgets for October 2026!")
                st.rerun()

    st.divider()

    # -------------------------------------------------------------------------
    # 2. BUDGET VS ACTUAL STATUS CARDS
    # -------------------------------------------------------------------------
    st.markdown("#### Category Budget Status (October 2026)")
    grid_cols = st.columns(4)
    for idx, item in enumerate(statuses):
        col = grid_cols[idx % 4]
        status_text = item["status"]
        color = (
            "#DC2626"
            if status_text == "OVER BUDGET"
            else ("#D97706" if status_text == "NEAR LIMIT" else "#16A34A")
        )
        with col:
            st.markdown(
                f"""
                <div class="sw-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong style="font-size:1.05rem;">{item['category']}</strong>
                        <span style="font-size:0.72rem;font-weight:700;color:{color};">{status_text}</span>
                    </div>
                    <hr style="margin:0.6rem 0;border:none;border-top:1px solid #F1F5F9;"/>
                    <div style="font-size:0.85rem;line-height:1.7;">
                        <div>Budget: <b>{format_inr(item['budget'])}</b></div>
                        <div>Spent: <b>{format_inr(item['spent'])}</b></div>
                        <div style="color:{color};font-weight:600;">Remaining: {format_inr(item['remaining'])}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            progress_val = min(max(item["utilization_pct"] / 100.0, 0.0), 1.0)
            st.progress(progress_val, text=f"{item['utilization_pct']}% of budget used")

    st.divider()

    # -------------------------------------------------------------------------
    # 3. TABULAR SUMMARY
    # -------------------------------------------------------------------------
    st.markdown("#### Complete Budget Ledger")
    table_df = pd.DataFrame(
        [
            {
                "Category": s["category"],
                "Monthly Budget": format_inr(s["budget"]),
                "Actual Spent": format_inr(s["spent"]),
                "Remaining": format_inr(s["remaining"]),
                "Utilization (%)": f"{s['utilization_pct']}%",
                "Status": s["status"],
            }
            for s in statuses
        ]
    )
    st.dataframe(table_df, use_container_width=True, hide_index=True)


render_budget_page()
