"""
SpendWise — Main Streamlit Application Entry Point
==================================================
Owner: Member 4 (Streamlit UI + OCR)

Responsibility:
- Configures the Streamlit page layout, custom professional financial CSS styling,
  and SQLite database initialization on startup.
- Login gate: until someone logs in, only `pages/login.py` is shown. After login the
  user's id is set with `set_current_user()` on every page load, so all pages and the
  AI agent only see that user's data.
- Implements multi-page navigation across all core modules:
  1. Home (`pages/home.py`)
  2. Transactions (`pages/transactions.py`)
  3. Upload Expense (`pages/upload.py`)
  4. Budget (`pages/budget.py`)
  5. Analytics (`pages/analytics.py`)
  6. AI Assistant (`pages/assistant.py`)
  7. My Profile & Setup (`pages/profile.py`)
- Does NOT contain business logic, database queries, or Pandas calculations.
"""

import streamlit as st
import streamlit.components.v1 as components
from utils.helpers import period_label
from database.database import init_db, set_current_user
from tools.auth_tool import LOGIN_COOKIE, LOGIN_DAYS, delete_login_token, user_for_login_token
from tools.database_tool import get_profile, get_transactions

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
        /* Cards use a soft tint + the theme's own text colour, so they work in dark AND light mode */
        .sw-card {
            background: rgba(148, 163, 184, 0.10);
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 14px;
            padding: 1.1rem 1.25rem;
            margin-bottom: 0.75rem;
            color: inherit;
        }
        .sw-card hr {
            border: none;
            border-top: 1px solid rgba(148, 163, 184, 0.25);
            margin: 0.6rem 0;
        }
        .sw-card-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        .sw-card-title {
            font-size: 1.05rem;
            font-weight: 700;
        }
        .sw-pill {
            font-size: 0.66rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            padding: 0.18rem 0.6rem;
            border-radius: 999px;
            white-space: nowrap;
            color: #FFFFFF;
        }
        .sw-kpi-label {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            opacity: 0.7;
            margin-bottom: 0.35rem;
        }
        .sw-kpi-value {
            font-size: 1.75rem;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            line-height: 1.2;
        }
        .sw-kpi-sub {
            font-size: 0.8rem;
            opacity: 0.75;
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

# -----------------------------------------------------------------------------
# LOGIN GATE: nobody sees any data before logging in
# -----------------------------------------------------------------------------
def _set_login_cookie(token: str, days: int) -> None:
    """Write (days > 0) or remove (days = 0) the "stay logged in" cookie in the browser."""
    components.html(
        f"""<script>
        const secure = window.parent.location.protocol === "https:" ? "; Secure" : "";
        window.parent.document.cookie = "{LOGIN_COOKIE}={token}; path=/; max-age={days * 86400}; SameSite=Strict" + secure;
        </script>""",
        height=0,
    )


# A refresh starts a new Streamlit session: log back in from the browser's login key
if st.session_state.get("user_id") is None:
    browser_key = st.context.cookies.get(LOGIN_COOKIE)
    remembered = user_for_login_token(browser_key) if isinstance(browser_key, str) else None
    if remembered:
        st.session_state["user_id"], st.session_state["username"] = remembered
        st.session_state["login_token"] = browser_key

set_current_user(st.session_state.get("user_id"))
if st.session_state.get("user_id") is None:
    if st.session_state.pop("clear_login_cookie", False):
        _set_login_cookie("", 0)
    st.navigation([st.Page("pages/login.py", title="Log in", icon="🔐")]).run()
    st.stop()

new_token = st.session_state.pop("write_login_cookie", None)  # set by pages/login.py right after logging in
if new_token:
    _set_login_cookie(new_token, LOGIN_DAYS)

# A brand-new account (no profile, no expenses) starts on the budget setup page,
# not on a dashboard full of empty cards. Afterwards it always starts on Home.
needs_setup = get_profile() is None and not get_transactions()

# Define multipage navigation using Streamlit's modern st.navigation API
pages = {
    "SpendWise Workspace": [
        st.Page("pages/home.py", title="Home Dashboard", icon="🏠", default=not needs_setup),
        st.Page("pages/transactions.py", title="Transactions", icon="🧾"),
        st.Page("pages/upload.py", title="Upload Expense", icon="📤"),
        st.Page("pages/budget.py", title="Budget Manager", icon="🎯"),
        st.Page("pages/analytics.py", title="Spending Analytics", icon="📊"),
        st.Page("pages/assistant.py", title="Ask SpendWise AI", icon="🤖"),
        st.Page("pages/profile.py", title="My Profile & Setup", icon="👤", default=needs_setup),
    ]
}

with st.sidebar:
    st.markdown("### 💳 SPENDWISE")
    st.caption("Autonomous Personal Financial Expense & Budgeting Assistant")
    st.divider()

pg = st.navigation(pages)

with st.sidebar:
    st.divider()
    st.markdown(f"👤 Logged in as **{st.session_state.get('username', '')}**")
    if st.button("Log out", width="stretch"):
        delete_login_token(st.session_state.get("login_token", ""))  # the browser's key stops working
        st.session_state.clear()  # also forgets this session's chat and agent memory
        st.session_state["clear_login_cookie"] = True
        st.rerun()
    st.caption(f"**Active Period:** {period_label()}")
    st.caption("**Architecture:** LangGraph + SQLite3 + Pandas + OCR")

pg.run()
