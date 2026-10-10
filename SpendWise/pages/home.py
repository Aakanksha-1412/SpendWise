"""
SpendWise — Home Dashboard Page
===============================
Owner: Member 4 (Streamlit UI + OCR)

Responsibility:
- Displays the executive financial overview:
  1. Header (`SPENDWISE — Autonomous Personal Financial Expense & Budgeting Assistant`)
  2. Clickable Quick-Action Navigation Cards ("Add Expense", "Upload Receipt",
     "View Transactions", "Manage Budget", "View Analytics", "Ask SpendWise")
  3. 4 Summary KPI Cards (Total Spent, Monthly Budget, Remaining Budget, Budget Alerts)
  4. Category Overview & Plotly Budget vs Actual Spending Chart
  5. Dynamic AI Insights & Discretionary Reallocation Suggestions
- Consumes processed metrics exclusively from `analytics/analytics.py`.
"""

import streamlit as st
import plotly.graph_objects as go

from analytics.analytics import (
    get_summary_metrics,
    get_budget_vs_actual_df,
    get_dashboard_ai_insights,
)
from utils.helpers import format_inr, period_label


def render_home_page() -> None:
    # -------------------------------------------------------------------------
    # 1. HEADER
    # -------------------------------------------------------------------------
    st.title("SPENDWISE")
    st.subheader("Autonomous Personal Financial Expense & Budgeting Assistant")
    st.caption(f"{period_label()} Financial Cycle · Real-Time SQLite & Pandas Telemetry · LangGraph Agent Ready")

    # -------------------------------------------------------------------------
    # 2. CLICKABLE QUICK-ACTION NAVIGATION CARDS
    # -------------------------------------------------------------------------
    st.markdown("#### Quick Navigation")
    nav_cols = st.columns(6)
    with nav_cols[0]:
        if st.button("➕ Add Expense", width="stretch"):
            st.switch_page("pages/transactions.py")
    with nav_cols[1]:
        if st.button("🧾 Upload Receipt", width="stretch"):
            st.switch_page("pages/upload.py")
    with nav_cols[2]:
        if st.button("📋 View Transactions", width="stretch"):
            st.switch_page("pages/transactions.py")
    with nav_cols[3]:
        if st.button("🎯 Manage Budget", width="stretch"):
            st.switch_page("pages/budget.py")
    with nav_cols[4]:
        if st.button("📊 View Analytics", width="stretch"):
            st.switch_page("pages/analytics.py")
    with nav_cols[5]:
        if st.button("🤖 Ask SpendWise", width="stretch", type="primary"):
            st.switch_page("pages/assistant.py")

    st.divider()

    # -------------------------------------------------------------------------
    # 3. SUMMARY KPI CARDS
    # -------------------------------------------------------------------------
    summary = get_summary_metrics()
    kpi_cols = st.columns(4)

    with kpi_cols[0]:
        st.markdown(
            f"""
            <div class="sw-card">
                <div class="sw-kpi-label">Total Spent (Oct 2026)</div>
                <div class="sw-kpi-value">{format_inr(summary['total_spent'])}</div>
                <div class="sw-kpi-sub">Across 8 active categories</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi_cols[1]:
        st.markdown(
            f"""
            <div class="sw-card">
                <div class="sw-kpi-label">Monthly Budget</div>
                <div class="sw-kpi-value">{format_inr(summary['monthly_budget'])}</div>
                <div class="sw-kpi-sub">Defined category limits</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi_cols[2]:
        rem_color = "#16A34A" if summary["remaining_budget"] >= 0 else "#DC2626"
        st.markdown(
            f"""
            <div class="sw-card">
                <div class="sw-kpi-label">Remaining Budget</div>
                <div class="sw-kpi-value" style="color: {rem_color};">{format_inr(summary['remaining_budget'])}</div>
                <div class="sw-kpi-sub">Available monthly buffer</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi_cols[3]:
        alert_count = summary["budget_alerts_count"]
        alert_color = "#DC2626" if alert_count > 0 else "#16A34A"
        st.markdown(
            f"""
            <div class="sw-card">
                <div class="sw-kpi-label">Budget Alerts</div>
                <div class="sw-kpi-value" style="color: {alert_color};">{alert_count} Active</div>
                <div class="sw-kpi-sub">Overruns & weekly spikes</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # 4. BUDGET VS ACTUAL CHART & AI INSIGHTS
    # -------------------------------------------------------------------------
    left_col, right_col = st.columns([1.55, 1.0], gap="large")

    bva_df = get_budget_vs_actual_df()

    with left_col:
        st.markdown("#### Budget vs Actual Spending by Category")
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name="Monthly Budget (₹)",
                x=bva_df["Category"],
                y=bva_df["Budget"],
                marker_color="#CBD5E1",
            )
        )
        fig.add_trace(
            go.Bar(
                name="Actual Spent (₹)",
                x=bva_df["Category"],
                y=bva_df["Spent"],
                marker_color=[
                    "#DC2626" if status == "OVER BUDGET" else "#0F766E"
                    for status in bva_df["Status"]
                ],
            )
        )
        fig.update_layout(
            barmode="group",
            height=370,
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(title="Amount (₹)", gridcolor="#F1F5F9"),
        )
        st.plotly_chart(fig, width="stretch")

    with right_col:
        st.markdown("#### 🧠 AI Financial Insights & Alerts")
        insights = get_dashboard_ai_insights()

        for ob in insights["over_budget_alerts"]:
            overrun_amt = format_inr(abs(ob["remaining"]))
            st.markdown(
                f"""
                <div class="sw-alert-box">
                    <strong>🚨 {ob['category']} Budget Alert</strong><br/>
                    Your <b>{ob['category']}</b> expenses ({format_inr(ob['spent'])}) have exceeded your monthly budget ({format_inr(ob['budget'])}) by <b>{overrun_amt}</b>.
                </div>
                """,
                unsafe_allow_html=True,
            )

        for spike in insights["spending_spikes"]:
            st.markdown(
                f"""
                <div class="sw-alert-box">
                    <strong>📈 Weekly Spending Spike — {spike['category']}</strong><br/>
                    {spike['message']}
                </div>
                """,
                unsafe_allow_html=True,
            )

        for suggestion in insights["reallocation_suggestions"]:
            st.markdown(
                f"""
                <div class="sw-suggestion-box">
                    <strong>💡 SpendWise Suggestion</strong><br/>
                    {suggestion}
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # -------------------------------------------------------------------------
    # 5. CATEGORY OVERVIEW GRID (ALL 8 OFFICIAL CATEGORIES)
    # -------------------------------------------------------------------------
    st.markdown(f"#### Category Overview ({period_label()})")
    cat_cols = st.columns(4)
    for idx, row in bva_df.iterrows():
        col = cat_cols[idx % 4]
        status_label = row["Status"]
        status_color = (
            "#DC2626"
            if status_label == "OVER BUDGET"
            else ("#D97706" if status_label == "NEAR LIMIT" else ("#64748B" if status_label == "NO BUDGET SET" else "#16A34A"))
        )
        with col:
            st.markdown(
                f"""
                <div class="sw-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong style="font-size:1rem;color:#0F172A;">{row['Category']}</strong>
                        <span style="font-size:0.72rem;font-weight:600;color:{status_color};">{status_label}</span>
                    </div>
                    <div style="margin-top:0.6rem;font-size:0.85rem;color:#475569;">
                        Spent: <b>{format_inr(row['Spent'])}</b> / {format_inr(row['Budget'])}
                    </div>
                    <div style="margin-top:0.2rem;font-size:0.82rem;color:{status_color};font-weight:600;">
                        Remaining: {format_inr(row['Remaining'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


render_home_page()
