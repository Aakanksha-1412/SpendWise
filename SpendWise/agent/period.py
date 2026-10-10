"""
SpendWise — Current Budget Period
=================================
Owner: Member 1 (AI Agent / LangGraph)

Responsibility:
- One place that answers "which month are we in?" for the agent tools and the
  offline fallback, so both always report the CURRENT month (not a hard-coded one).
"""

from datetime import datetime
from typing import Dict


def this_month() -> Dict[str, int]:
    """Keyword arguments for teammates' month-based functions: {"month": 11, "year": 2026}."""
    now = datetime.now()
    return {"month": now.month, "year": now.year}


def this_month_label() -> str:
    """Readable name of the current month, e.g. "November 2026"."""
    return datetime.now().strftime("%B %Y")
