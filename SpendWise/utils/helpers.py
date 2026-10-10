"""
SpendWise — Shared Utilities & Constants
========================================
Responsibility:
- Provides shared constants (official expense categories, discretionary flags, color map).
- Provides currency formatting (INR ₹), date normalization, and Streamlit navigation helpers.
- Used across UI pages, tools, and analytics modules without creating circular dependencies.
"""

from datetime import datetime
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
    Format a numeric value in Indian Rupee (₹) notation with comma separators.
    Example: 6100 -> '₹6,100' | -2100 -> '-₹2,100'
    """
    is_negative = amount < 0
    abs_val = abs(round(float(amount), 2))
    if abs_val.is_integer():
        formatted = f"{int(abs_val):,}"
    else:
        formatted = f"{abs_val:,.2f}"

    if is_negative:
        return f"-₹{formatted}"
    if include_sign and amount > 0:
        return f"+₹{formatted}"
    return f"₹{formatted}"


def normalize_date(date_str: str) -> str:
    """
    Normalize input dates (YYYY-MM-DD or DD-MM-YYYY) into standard DD-MM-YYYY display format.
    """
    if not date_str:
        return datetime.now().strftime("%d-%m-%Y")

    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
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
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
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


def get_setting(name: str, default: str = "") -> str:
    """
    Read a setting from real environment variables, else from SpendWise/.env.
    (Use for GEMINI_API_KEY, GEMINI_MODEL, SPENDWISE_SEED_DEMO, TESSERACT_CMD_PATH, ...)
    """
    import os

    value = os.getenv(name)
    if value is None:
        try:
            from dotenv import dotenv_values

            env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
            value = dotenv_values(env_file).get(name)
        except ImportError:
            value = None
    return (value if value is not None else default).strip()
