"""
SpendWise — Shared Utilities & Constants
========================================
Responsibility:
- Provides shared constants (official expense categories, discretionary flags, color map).
- Provides currency formatting (INR ₹), date normalization, and Streamlit navigation helpers.
- Used across UI pages, tools, and analytics modules without creating circular dependencies.
"""

import os
from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

# Official SpendWise Expense Categories
CATEGORIES: List[str] = [
    "Food",
    "Transport",
    "Shopping",
    "Entertainment",
    "Bills",
    "Healthcare",
    "Education",
    "Others",
]

# Categories considered discretionary (candidates for budget reallocation suggestions)
DISCRETIONARY_CATEGORIES: List[str] = [
    "Shopping",
    "Entertainment",
    "Food",
    "Others",
]

# Essential categories (non-discretionary fixed/priority expenses)
ESSENTIAL_CATEGORIES: List[str] = [
    "Bills",
    "Healthcare",
    "Education",
    "Transport",
]

# Consistent color palette for Plotly charts across Home and Analytics pages
CATEGORY_COLORS: Dict[str, str] = {
    "Food": "#0F766E",          # Deep Teal
    "Transport": "#0369A1",     # Ocean Blue
    "Shopping": "#DC2626",      # Crimson Alert
    "Entertainment": "#7C3AED", # Violet
    "Bills": "#475569",         # Slate
    "Healthcare": "#16A34A",    # Emerald
    "Education": "#D97706",     # Amber
    "Others": "#64748B",        # Cool Gray
}


def format_inr(amount: float, include_sign: bool = False) -> str:
    """
    Format a numeric value in Indian Rupee (₹) notation with Indian digit grouping
    (last three digits, then groups of two).
    Example: 6100 -> '₹6,100' | 200000 -> '₹2,00,000' | -2100 -> '-₹2,100'
    """
    is_negative = amount < 0
    abs_val = abs(round(float(amount), 2))
    rupees, paise = f"{abs_val:.2f}".split(".")
    head, last_three = rupees[:-3], rupees[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    formatted = ",".join(groups + [last_three])
    if not abs_val.is_integer():
        formatted += f".{paise}"

    if is_negative:
        return f"-₹{formatted}"
    if include_sign and amount > 0:
        return f"+₹{formatted}"
    return f"₹{formatted}"


# Date formats SpendWise understands, including those in Indian bank exports
# ("25 Oct 2026", "25-Oct-2026", "25/10/26"). Four-digit years are tried first.
DATE_FORMATS = (
    "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d",
    "%d %b %Y", "%d-%b-%Y", "%d %B %Y", "%d-%B-%Y",
    "%d/%m/%y", "%d-%m-%y", "%d %b %y", "%d-%b-%y",
)


def normalize_date(date_str: str) -> str:
    """
    Normalize input dates (DD-MM-YYYY, YYYY-MM-DD, 25 Oct 2026, 25/10/26, ...) into
    standard DD-MM-YYYY display format.
    """
    if not date_str:
        return datetime.now().strftime("%d-%m-%Y")

    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            continue
    return date_str.strip()


def to_iso_date(date_str: str) -> str:
    """
    Convert DD-MM-YYYY or YYYY-MM-DD into ISO YYYY-MM-DD for chronological sorting and Pandas filtering.
    """
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now().strftime("%Y-%m-%d")


def resolve_period(month: Optional[int] = None, year: Optional[int] = None) -> Tuple[int, int]:
    """
    Return (month, year), using the CURRENT month/year for anything not given.
    Lets every budget/analytics function default to "this month" instead of a fixed date.
    """
    now = datetime.now()
    return (month or now.month, year or now.year)


def period_label(month: Optional[int] = None, year: Optional[int] = None) -> str:
    """Readable month name, e.g. "November 2026" (current month by default)."""
    month, year = resolve_period(month, year)
    return datetime(year, month, 1).strftime("%B %Y")


# SpendWise/.env — read by get_setting(); tests point this somewhere else.
ENV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
# Gemini model used by the agent and receipt OCR unless GEMINI_MODEL is set.
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"


def get_setting(name: str, default: str = "") -> str:
    """
    Read a setting from real environment variables, else from SpendWise/.env, else from
    Streamlit secrets (the "Secrets" box on Streamlit Community Cloud).
    (Use for GEMINI_API_KEY, GEMINI_MODEL, SPENDWISE_SEED_DEMO, TESSERACT_CMD_PATH, ...)
    The .env file is parsed again only when it changes, so editing it needs no restart.
    """
    value = os.getenv(name)
    if value is None:
        try:
            modified_time = os.path.getmtime(ENV_FILE_PATH)
        except OSError:
            modified_time = 0.0
        value = _env_file_values(ENV_FILE_PATH, modified_time).get(name)
    if value is None:
        value = _streamlit_secret(name)
    return (value if value is not None else default).strip()


def _streamlit_secret(name: str) -> Optional[str]:
    """A value from .streamlit/secrets.toml / the Cloud "Secrets" box, or None if there isn't one."""
    try:
        import streamlit as st

        return str(st.secrets[name]) if name in st.secrets else None
    except Exception:  # no secrets file (normal when running locally with .env)
        return None


@lru_cache(maxsize=4)
def _env_file_values(path: str, modified_time: float) -> Dict[str, Optional[str]]:
    """Parsed .env contents, cached per file version (a new modified time = re-read)."""
    try:
        from dotenv import dotenv_values
    except ImportError:
        return {}
    return dotenv_values(path) if modified_time else {}


def expense_date_error(date_str: str) -> Optional[str]:
    """
    An expense date must be a real calendar date, today or earlier (empty = today).
    Returns the message to show when it isn't, otherwise None.
    """
    normalized = normalize_date(date_str or "")
    try:
        parsed = datetime.strptime(normalized, "%d-%m-%Y").date()
    except ValueError:
        example = datetime.now().strftime("%d-%m-%Y")
        return f'"{(date_str or "").strip()}" is not a real date. Please write the date as DD-MM-YYYY, for example {example}.'
    if parsed > datetime.now().date():
        return f"The date {normalized} is in the future. Please use today's date or an earlier one."
    return None


def is_in_current_month(date_str: str) -> bool:
    """True if a DD-MM-YYYY (or other common format) date is in the current month."""
    try:
        parsed = datetime.strptime(normalize_date(date_str or ""), "%d-%m-%Y")
    except ValueError:
        return False
    now = datetime.now()
    return parsed.month == now.month and parsed.year == now.year
