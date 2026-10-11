"""
SpendWise — Log in / Create account
===================================
Owner: Member 4 (Streamlit UI + OCR)

Responsibility:
- Shown by app.py whenever nobody is logged in.
- Log in with username + password, or create an account (optionally with demo data, or
  taking over the data already saved on this computer).
- All account logic lives in `tools/auth_tool.py` (passwords are stored only as hashes).
"""

import streamlit as st

from tools.auth_tool import create_user, has_unowned_data, unowned_data_summary, verify_user
from utils.helpers import get_setting


def _log_in(user_id: int, username: str) -> None:
    st.session_state["user_id"] = user_id
    st.session_state["username"] = username.strip()
    st.rerun()


def render_login_page() -> None:
    st.title("💳 SPENDWISE")
    st.caption("Autonomous Personal Financial Expense & Budgeting Assistant")

    tab_login, tab_signup = st.tabs(["🔐 Log in", "✨ Create account"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.form_submit_button("Log in", type="primary"):
                user_id = verify_user(username, password)
                if user_id is None:
                    st.error("Wrong username or password.")
                else:
                    _log_in(user_id, username)

    with tab_signup:
        with st.form("signup_form"):
            new_username = st.text_input("Choose a username", key="signup_username")
            new_password = st.text_input("Choose a password (at least 6 characters)", type="password", key="signup_password")
            confirm = st.text_input("Type the password again", type="password", key="signup_confirm")
            with_demo = st.checkbox(
                "Start with demo data (sample expenses, useful to explore or present)", key="signup_demo"
            )
            claim = False
            if has_unowned_data():
                claim = st.checkbox(
                    f"Move the data saved on this computer before login ({unowned_data_summary()}) into my account. "
                    "Leave unticked to start with an empty account.",
                    value=False,
                    key="signup_claim",
                )
            if st.form_submit_button("Create account", type="primary"):
                if new_password != confirm:
                    st.error("The two passwords are different.")
                else:
                    ok, result = create_user(
                        new_username, new_password, with_demo_data=with_demo and not claim, claim_existing_data=claim
                    )
                    if ok:
                        _log_in(result, new_username)
                    else:
                        st.error(result)

    st.caption("🔒 Passwords are stored only as secure hashes, never as plain text.")
    if get_setting("SPENDWISE_ONLINE_DEMO").lower() in ("true", "1", "yes"):
        st.info(
            "🌐 **Online demo** — accounts and data may be reset when the server restarts, and uploaded "
            "receipts are read by Google Gemini. Please don't enter real bank details or private bills."
        )


render_login_page()
