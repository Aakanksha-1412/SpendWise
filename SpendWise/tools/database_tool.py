"""
SpendWise — Database Tool Layer
===============================
Owner: Member 2 (Database + Categorization)

Responsibility:
- Exposes clean Python functions & LangChain tool interfaces for reading/writing
  transactions and budgets in SQLite.
- Ensures UI pages (`pages/*.py`) and the AI Agent (`agent/graph.py`) never execute
  raw SQL strings directly.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None  # type: ignore
    PANDAS_AVAILABLE = False

from database.database import get_connection, init_db
from tools.categorization_tool import remember_merchant_category
from utils.helpers import normalize_date, resolve_period, CATEGORIES


def add_transaction(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a single transaction into the SQLite `transactions` table.

    Parameters
    ----------
    transaction : dict
        Expected keys:
        - date (str): DD-MM-YYYY or YYYY-MM-DD
        - merchant (str): Name of merchant
        - amount (float): Expense amount in INR
        - category (str): One of the official 8 categories
        - description (str, optional): Notes/items
        - source (str, optional): 'Text' | 'CSV' | 'Receipt'

    Returns
    -------
    dict : The newly created transaction record including `id` and `created_at`.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    date_str = normalize_date(str(transaction.get("date", "")))
    merchant = str(transaction.get("merchant", "Unknown Merchant")).strip()
    amount = float(transaction.get("amount", 0.0))
    category = str(transaction.get("category", "Others")).strip()
    if category not in CATEGORIES:
        category = "Others"
    description = str(transaction.get("description", "")).strip()
    source = str(transaction.get("source", "Text")).strip()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO transactions (date, merchant, amount, category, description, source, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (date_str, merchant, amount, category, description, source, created_at),
    )
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Teach ChromaDB semantic memory this merchant -> category (never blocks saving)
    remember_merchant_category(merchant, category)

    return {
        "id": new_id,
        "date": date_str,
        "merchant": merchant,
        "amount": amount,
        "category": category,
        "description": description,
        "source": source,
        "created_at": created_at,
    }


def bulk_insert_transactions(transactions: List[Dict[str, Any]]) -> int:
    """
    Insert multiple transactions (e.g., from CSV upload) into SQLite.
    Returns count of inserted records.
    """
    inserted_count = 0
    for tx in transactions:
        add_transaction(tx)
        inserted_count += 1
    return inserted_count


def get_transactions(
    category: Optional[str] = None,
    merchant_query: Optional[str] = None,
    date_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve transactions from SQLite with optional filters for category, merchant, and date.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT id, date, merchant, amount, category, description, source, created_at FROM transactions WHERE 1=1"
    params: List[Any] = []

    if category and category != "All":
        query += " AND category = ?"
        params.append(category)

    if merchant_query and merchant_query.strip():
        query += " AND LOWER(merchant) LIKE ?"
        params.append(f"%{merchant_query.strip().lower()}%")

    if date_filter and date_filter.strip():
        normalized = normalize_date(date_filter)
        query += " AND date = ?"
        params.append(normalized)

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_transactions_df() -> Any:
    """
    Return all transactions as a Pandas DataFrame for analytics and budget comparisons.
    Falls back to a list of dicts if Pandas is not yet installed in the environment.
    """
    records = get_transactions()
    if not PANDAS_AVAILABLE:
        return records
    if not records:
        return pd.DataFrame(
            columns=["id", "date", "merchant", "amount", "category", "description", "source", "created_at"]
        )
    return pd.DataFrame(records)


def get_category_spending(category: str, month: Optional[int] = None, year: Optional[int] = None) -> float:
    """
    Calculate total spending for a specific category in a given month/year (default: this month)
    using Pandas (with pure Python fallback if Pandas is not installed).
    """
    month, year = resolve_period(month, year)
    if PANDAS_AVAILABLE:
        df = get_transactions_df()
        if df.empty:
            return 0.0
        df["parsed_date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
        mask = (
            (df["category"].str.lower() == category.strip().lower())
            & (df["parsed_date"].dt.month == month)
            & (df["parsed_date"].dt.year == year)
        )
        return float(df.loc[mask, "amount"].sum())

    # Pure Python fallback
    records = get_transactions()
    total = 0.0
    for r in records:
        if r["category"].strip().lower() == category.strip().lower():
            try:
                dt = datetime.strptime(r["date"], "%d-%m-%Y")
                if dt.month == month and dt.year == year:
                    total += float(r["amount"])
            except ValueError:
                continue
    return round(total, 2)


def get_all_budgets(month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, float]:
    """
    Retrieve monthly budget allocations for all categories for the given month (default: this month).
    If a category has no budget saved for that month yet, its most recent earlier budget is
    carried over (so a new month doesn't start with every budget at ₹0).
    """
    month, year = resolve_period(month, year)
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT category, monthly_budget FROM budgets
        WHERE year * 12 + month <= ?
        ORDER BY year * 12 + month DESC
        """,
        (year * 12 + month,),
    )
    rows = cursor.fetchall()
    conn.close()

    budget_map = {cat: 0.0 for cat in CATEGORIES}
    found = set()
    for row in rows:  # newest first: keep the first (latest) budget seen per category
        if row["category"] in budget_map and row["category"] not in found:
            budget_map[row["category"]] = float(row["monthly_budget"])
            found.add(row["category"])
    return budget_map


def upsert_budget(category: str, monthly_budget: float, month: Optional[int] = None, year: Optional[int] = None) -> None:
    """
    Create or update the monthly budget for a given category (default: this month).
    """
    month, year = resolve_period(month, year)
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO budgets (category, monthly_budget, month, year)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(category, month, year)
        DO UPDATE SET monthly_budget = excluded.monthly_budget
        """,
        (category, float(monthly_budget), month, year),
    )
    conn.commit()
    conn.close()
