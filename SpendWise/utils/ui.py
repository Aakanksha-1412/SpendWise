"""
SpendWise — small Streamlit pieces shared by several pages.
"""

import streamlit as st

from analytics.analytics import get_income_alerts


def show_income_alerts() -> None:
    """Show this month's problems compared to the user's income (nothing without a profile)."""
    for level, message in get_income_alerts():
        (st.error if level == "error" else st.warning)(message)
