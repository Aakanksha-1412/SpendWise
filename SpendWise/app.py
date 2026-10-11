"""
SpendWise — Main Streamlit Application Entry Point
==================================================
Owner: Member 4 (Streamlit UI + OCR)

Responsibility:
- Configures the Streamlit page layout, custom professional financial CSS styling,
  and SQLite database initialization on startup.
- Implements multi-page navigation across all 6 core modules:
  1. Home (`pages/home.py`)
  2. Transactions (`pages/transactions.py`)
  3. Upload Expense (`pages/upload.py`)
  4. Budget (`pages/budget.py`)
  5. Analytics (`pages/analytics.py`)
  6. AI Assistant (`pages/assistant.py`)
- Does NOT contain business logic, database queries, or Pandas calculations.
"""

import streamlit as st
from utils.helpers import period_label
from database.database import init_db

# Ensure SQLite tables and initial demo records exist before rendering any page
init_db()

st.set_page_config(
    page_title="SPENDWISE — Autonomous Personal Financial Expense & Budgeting Assistant",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject clean, modern financial dashboard CSS
st.markdown(
    """
    <style>
        /* Professional financial typography & spacing */
        .block-container {
            padding-top: 1.75rem;
            padding-bottom: 2.5rem;
            max-width: 1280px;
        }
        .sw-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
        }
        .sw-kpi-label {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748B;
            margin-bottom: 0.35rem;
        }
        .sw-kpi-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0F172A;
            font-variant-numeric: tabular-nums;
            line-height: 1.2;
        }
        .sw-kpi-sub {
            font-size: 0.8rem;
            color: #475569;
            margin-top: 0.35rem;
        }
        .sw-alert-box {
            background-color: #FEF2F2;
            border-left: 4px solid #DC2626;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.85rem;
            color: #7F1D1D;
        }
        .sw-suggestion-box {
            background-color: #F0FDF4;
            border-left: 4px solid #16A34A;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.85rem;
            color: #14532D;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Define multipage navigation using Streamlit's modern st.navigation API
pages = {
    "SpendWise Workspace": [
        st.Page("pages/home.py", title="Home Dashboard", icon="🏠", default=True),
        st.Page("pages/transactions.py", title="Transactions", icon="🧾"),
        st.Page("pages/upload.py", title="Upload Expense", icon="📤"),
        st.Page("pages/budget.py", title="Budget Manager", icon="🎯"),
        st.Page("pages/analytics.py", title="Spending Analytics", icon="📊"),
        st.Page("pages/assistant.py", title="Ask SpendWise AI", icon="🤖"),
        st.Page("pages/profile.py", title="My Profile & Setup", icon="👤"),
    ]
}

with st.sidebar:
    st.markdown("### 💳 SPENDWISE")
    st.caption("Autonomous Personal Financial Expense & Budgeting Assistant")
    st.divider()

pg = st.navigation(pages)

with st.sidebar:
    st.divider()
    st.caption(f"**Active Period:** {period_label()}")
    st.caption("**Architecture:** LangGraph + SQLite3 + Pandas + OCR")

pg.run()
