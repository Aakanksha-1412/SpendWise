"""
SpendWise — Financial Analytics & Spike Detection Page
======================================================
Owner: Member 4 (Streamlit UI) — consumes `analytics/` & `tools/spike_detector.py` (Member 3)

Responsibility:
- Renders the 6 required analytical views using Plotly and Pandas DataFrames
  from `analytics/analytics.py` and `tools/spike_detector.py`:
  1. Category-wise spending
  2. Budget vs actual comparison
  3. Weekly spending comparison
  4. Monthly spending overview
  5. Daily & cumulative spending trends
  6. Automated Spending Spike Detection alerts
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from analytics.analytics import (
    get_category_spending_df,
    get_budget_vs_actual_df,
    get_weekly_comparison_df,
    get_monthly_spending_df,
    get_spending_trends_df,
)
from tools.spike_detector import detect_all_category_spikes
from utils.helpers import format_inr, CATEGORY_COLORS, period_label


def render_analytics_page() -> None:
    st.title("📊 Financial Analytics & Spike Detection")
    st.caption("Powered by Pandas aggregations (`analytics/analytics.py`) and anomaly detection (`tools/spike_detector.py`).")

    # -------------------------------------------------------------------------
    # 6. SPENDING SPIKE DETECTION BANNER
    # -------------------------------------------------------------------------
    st.markdown("#### 🚨 Automated Spending Spike Detection")
    spikes = detect_all_category_spikes()
    active_spikes = [s for s in spikes if s["spike_detected"]]

    if active_spikes:
        for sp in active_spikes:
            st.markdown(
                f"""
                <div class="sw-alert-box">
                    <strong>🚨 Spending Spike Detected — {sp['category']} ({sp['change_label']})</strong><br/>
                    Previous weekly {sp['category']} spending: <b>{format_inr(sp['previous_weekly_spending'])}</b> ·
                    Current weekly {sp['category']} spending: <b>{format_inr(sp['current_weekly_spending'])}</b><br/>
                    <span>{sp['message']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.success("No unusual weekly spending spikes detected across categories.")

    st.divider()

    # -------------------------------------------------------------------------
    # 1. CATEGORY-WISE SPENDING & 2. BUDGET VS ACTUAL
    # -------------------------------------------------------------------------
    row1_col1, row1_col2 = st.columns(2, gap="large")

    cat_df = get_category_spending_df()
    bva_df = get_budget_vs_actual_df()

    with row1_col1:
        st.markdown("#### 1. Category-Wise Spending Distribution")
        fig_pie = px.pie(
            cat_df,
            names="Category",
            values="Spent",
            hole=0.48,
            color="Category",
            color_discrete_map=CATEGORY_COLORS,
        )
        fig_pie.update_layout(height=350, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_pie, width="stretch")

    with row1_col2:
        st.markdown("#### 2. Budget vs Actual Spending")
        fig_bva = go.Figure()
        fig_bva.add_trace(
            go.Bar(name="Budget (₹)", x=bva_df["Category"], y=bva_df["Budget"], marker_color="#CBD5E1")
        )
        fig_bva.add_trace(
            go.Bar(name="Actual (₹)", x=bva_df["Category"], y=bva_df["Spent"], marker_color="#0F766E")
        )
        fig_bva.update_layout(
            barmode="group",
            height=350,
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", y=1.08),
        )
        st.plotly_chart(fig_bva, width="stretch")

    st.divider()

    # -------------------------------------------------------------------------
    # 3. WEEKLY SPENDING & 4. MONTHLY SPENDING
    # -------------------------------------------------------------------------
    row2_col1, row2_col2 = st.columns(2, gap="large")

    weekly_df = get_weekly_comparison_df()
    monthly_df = get_monthly_spending_df()

    with row2_col1:
        st.markdown("#### 3. Weekly Spending Comparison (Prev vs Current Week)")
        fig_wk = go.Figure()
        fig_wk.add_trace(
            go.Bar(
                name="Previous Week (₹)",
                x=weekly_df["Category"],
                y=weekly_df["Previous Week (₹)"],
                marker_color="#94A3B8",
            )
        )
        fig_wk.add_trace(
            go.Bar(
                name="Current Week (₹)",
                x=weekly_df["Category"],
                y=weekly_df["Current Week (₹)"],
                marker_color="#0369A1",
            )
        )
        fig_wk.update_layout(
            barmode="group",
            height=340,
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", y=1.08),
        )
        st.plotly_chart(fig_wk, width="stretch")

    with row2_col2:
        st.markdown("#### 4. Monthly Spending Overview")
        fig_mo = px.bar(
            monthly_df,
            x="Month",
            y="Total_Spent",
            text_auto=".2s",
            color_discrete_sequence=["#0F766E"],
        )
        fig_mo.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title="Total Spend (₹)",
        )
        st.plotly_chart(fig_mo, width="stretch")

    st.divider()

    # -------------------------------------------------------------------------
    # 5. SPENDING TRENDS (DAILY & CUMULATIVE)
    # -------------------------------------------------------------------------
    st.markdown(f"#### 5. {period_label()} Daily & Cumulative Spending Trend")
    trend_df = get_spending_trends_df()
    if not trend_df.empty:
        fig_trend = go.Figure()
        fig_trend.add_trace(
            go.Bar(
                name="Daily Spend (₹)",
                x=trend_df["Date"],
                y=trend_df["Daily_Spent"],
                marker_color="#94A3B8",
            )
        )
        fig_trend.add_trace(
            go.Scatter(
                name="Cumulative Spend (₹)",
                x=trend_df["Date"],
                y=trend_df["Cumulative_Spent"],
                mode="lines+markers",
                line=dict(color="#0F766E", width=3),
            )
        )
        fig_trend.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(orientation="h", y=1.08),
        )
        st.plotly_chart(fig_trend, width="stretch")


render_analytics_page()
