"""
SpendWise — Database Tool Layer
===============================
Owner: Member 2 (Database + Categorization)

Responsibility:
- Exposes clean Python functions & LangChain tool interfaces for reading/writing
  transactions and budgets in SQLite.
- Every function reads/writes only the LOGGED-IN user's rows (`current_user_id()`).
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

from database.database import current_user_id, get_connection, init_db
from tools.categorization_tool import remember_merchant_categories, remember_merchant_category
from utils.helpers import normalize_date, resolve_period, CATEGORIES


def add_transaction(transaction: Dict[str, Any], learn_category: bool = True) -> Dict[str, Any]:
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

    learn_category : bool
        Teach ChromaDB this merchant -> category (bulk imports do it once at the end).

    Returns
    -------
    dict : The newly created transaction record including `id` and `created_at`.
    """
    saved = _insert_transactions([transaction])[0]

    # Teach ChromaDB semantic memory this merchant -> category (never blocks saving)
    if learn_category:
        remember_merchant_category(saved["merchant"], saved["category"])
    return saved


def bulk_insert_transactions(transactions: List[Dict[str, Any]]) -> int:
    """
    Insert multiple transactions (e.g., from CSV upload) into SQLite.
    All of them are saved, or (if any fails) none. Returns count of inserted records.
    """
    saved = _insert_transactions(transactions)
    remember_merchant_categories([(tx["merchant"], tx["category"]) for tx in saved])  # one ChromaDB write
    return len(saved)


def _insert_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean and insert rows in ONE database transaction (all or nothing); always closes the connection."""
    init_db()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    saved = []
    conn = get_connection()
    try:
        with conn:  # commits at the end, or rolls everything back on an error
            for transaction in transactions:
                date_str = normalize_date(str(transaction.get("date", "")))
                merchant = str(transaction.get("merchant", "Unknown Merchant")).strip()
                amount = float(transaction.get("amount", 0.0))
                # Accept any spelling case ("food", "FOOD" -> "Food"); unknown names become "Others"
                category_text = str(transaction.get("category", "Others")).strip().lower()
                category = next((official for official in CATEGORIES if official.lower() == category_text), "Others")
                description = str(transaction.get("description", "")).strip()
                source = str(transaction.get("source", "Text")).strip()
                cursor = conn.execute(
                    """
                    INSERT INTO transactions (user_id, date, merchant, amount, category, description, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (current_user_id(), date_str, merchant, amount, category, description, source, created_at),
                )
                saved.append({
                    "id": cursor.lastrowid,
                    "date": date_str,
                    "merchant": merchant,
                    "amount": amount,
                    "category": category,
                    "description": description,
                    "source": source,
                    "created_at": created_at,
                })
    finally:
        conn.close()
    return saved


def get_transactions(
    category: Optional[str] = None,
    merchant_query: Optional[str] = None,
    date_filter: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve transactions from SQLite with optional filters for category, merchant, date,
    and month (month + year together). Newest entry first.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    query = (
        "SELECT id, date, merchant, amount, category, description, source, created_at "
        "FROM transactions WHERE user_id = ?"
    )
    params: List[Any] = [current_user_id()]

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

    if month and year:
        query += " AND substr(date, 4, 7) = ?"  # DD-MM-YYYY -> "MM-YYYY"
        params.append(f"{int(month):02d}-{int(year)}")

    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_transaction_months() -> List[tuple]:
    """(month, year) pairs that have expenses, newest first (unreadable dates are skipped)."""
    months = set()
    for row in get_transactions():
        try:
            parsed = datetime.strptime(row["date"], "%d-%m-%Y")
        except ValueError:
            continue
        months.add((parsed.month, parsed.year))
    return sorted(months, key=lambda m: (m[1], m[0]), reverse=True)


def update_transaction(transaction_id: int, changes: Dict[str, Any]) -> bool:
    """
    Change one of THIS user's expenses (date, merchant, amount, category, description).
    Returns False if it doesn't exist or belongs to someone else.
    """
    allowed = {key: changes[key] for key in ("date", "merchant", "amount", "category", "description") if key in changes}
    if "date" in allowed:
        allowed["date"] = normalize_date(str(allowed["date"]))
    if "category" in allowed:
        category_text = str(allowed["category"]).strip().lower()
        allowed["category"] = next((c for c in CATEGORIES if c.lower() == category_text), "Others")
    if not allowed:
        return False
    init_db()
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                f"UPDATE transactions SET {', '.join(f'{key} = ?' for key in allowed)} WHERE id = ? AND user_id = ?",
                (*allowed.values(), int(transaction_id), current_user_id()),
            )
    finally:
        conn.close()
    return cursor.rowcount == 1


def delete_transaction(transaction_id: int) -> bool:
    """Delete one of THIS user's expenses. Returns False if it doesn't exist or isn't theirs."""
    init_db()
    conn = get_connection()
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM transactions WHERE id = ? AND user_id = ?", (int(transaction_id), current_user_id())
            )
    finally:
        conn.close()
    return cursor.rowcount == 1


def expense_already_saved(date: str, merchant: str, amount: float) -> bool:
    """True if this user already has an expense with the same date, merchant (any case) and amount."""
    init_db()
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM transactions WHERE user_id = ? AND date = ? AND LOWER(TRIM(merchant)) = ? AND ROUND(amount, 2) = ?",
        (current_user_id(), normalize_date(date), merchant.strip().lower(), round(float(amount), 2)),
    ).fetchone()
    conn.close()
    return row is not None


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


def get_spending_by_category(month: Optional[int] = None, year: Optional[int] = None) -> Dict[str, float]:
    """
    Total spending per official category for a month (default: this month), loading the
    transactions only ONCE. Same rules as get_category_spending (category name ignores case).
    """
    month, year = resolve_period(month, year)
    totals = {cat: 0.0 for cat in CATEGORIES}
    by_lower = {cat.lower(): cat for cat in CATEGORIES}
    if PANDAS_AVAILABLE:
        df = get_transactions_df()
        if df.empty:
            return totals
        df["parsed_date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
        month_df = df[(df["parsed_date"].dt.month == month) & (df["parsed_date"].dt.year == year)]
        for category, amount in month_df.groupby(month_df["category"].str.strip().str.lower())["amount"].sum().items():
            if category in by_lower:
                totals[by_lower[category]] = float(amount)
        return totals

    for r in get_transactions():
        official = by_lower.get(r["category"].strip().lower())
        try:
            dt = datetime.strptime(r["date"], "%d-%m-%Y")
        except ValueError:
            continue
        if official and dt.month == month and dt.year == year:
            totals[official] += float(r["amount"])
    return {cat: round(total, 2) for cat, total in totals.items()}


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
        WHERE user_id = ? AND year * 12 + month <= ?
        ORDER BY year * 12 + month DESC
        """,
        (current_user_id(), year * 12 + month),
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
        INSERT INTO budgets (user_id, category, monthly_budget, month, year)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, category, month, year)
        DO UPDATE SET monthly_budget = excluded.monthly_budget
        """,
        (current_user_id(), category, float(monthly_budget), month, year),
    )
    conn.commit()
    conn.close()


# ==============================================================================
# USER PROFILE (income, savings goal, usual monthly spending)
# ==============================================================================
def get_profile() -> Optional[Dict[str, Any]]:
    """
    The user's profile, or None if they haven't set one up yet:
    {"monthly_income": float, "savings_goal": float, "usual_spending": {category: float, ...}}
    """
    init_db()
    conn = get_connection()
    user_id = current_user_id()
    row = conn.execute("SELECT monthly_income, savings_goal FROM profile WHERE user_id = ?", (user_id,)).fetchone()
    usual = {cat: 0.0 for cat in CATEGORIES}
    for r in conn.execute("SELECT category, amount FROM usual_spending WHERE user_id = ?", (user_id,)):
        if r["category"] in usual:
            usual[r["category"]] = float(r["amount"])
    conn.close()
    if row is None:
        return None
    return {
        "monthly_income": float(row["monthly_income"]),
        "savings_goal": float(row["savings_goal"]),
        "usual_spending": usual,
    }


def save_profile(monthly_income: float, savings_goal: float, usual_spending: Dict[str, float]) -> None:
    """Create or update the profile and the usual spending per category (missing = 0)."""
    init_db(allow_demo=False)
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO profile (user_id, monthly_income, savings_goal, updated_at) VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET monthly_income = excluded.monthly_income,
            savings_goal = excluded.savings_goal, updated_at = excluded.updated_at
        """,
        (current_user_id(), float(monthly_income), float(savings_goal), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.executemany(
        """
        INSERT INTO usual_spending (user_id, category, amount) VALUES (?, ?, ?)
        ON CONFLICT(user_id, category) DO UPDATE SET amount = excluded.amount
        """,
        [(current_user_id(), cat, float(usual_spending.get(cat, 0.0) or 0.0)) for cat in CATEGORIES],
    )
    conn.commit()
    conn.close()


def remove_all_data() -> int:
    """
    "Start fresh": delete ALL of this user's transactions and budgets (e.g. the demo data).
    Returns how many transactions were removed. Save a profile right after, so demo data
    is not added again.
    """
    init_db(allow_demo=False)
    conn = get_connection()
    removed = conn.execute("DELETE FROM transactions WHERE user_id = ?", (current_user_id(),)).rowcount
    conn.execute("DELETE FROM budgets WHERE user_id = ?", (current_user_id(),))
    conn.commit()
    conn.close()
    return removed
