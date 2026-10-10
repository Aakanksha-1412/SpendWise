"""
SpendWise — SQLite Database Connection & Initialization
=======================================================
Owner: Member 2 (Database + Categorization)

Responsibility:
- Manages the SQLite3 database connection (`spendwise.db`).
- Initializes the required tables (`transactions` and `budgets`).
- Seeds realistic initial demo data on first run so the dashboard and analytics
  work out-of-the-box for all team members. Demo dates are relative to TODAY, so the
  demo always shows "this month" and "this week" data.
- Set SPENDWISE_SEED_DEMO=false (in SpendWise/.env) to start with EMPTY tables and
  use only your real expenses. (Only affects a new/empty database: delete
  data/spendwise.db to start over.)
- NOTE: UI pages (`pages/*.py`) must NEVER write raw SQL queries directly.
  All reads/writes go through `tools/database_tool.py`.
"""

import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional

from utils.helpers import get_setting

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("SPENDWISE_DB_PATH", os.path.join(PROJECT_DIR, "data", "spendwise.db"))


def seed_demo_enabled() -> bool:
    """SPENDWISE_SEED_DEMO from the environment or SpendWise/.env (default: true)."""
    return get_setting("SPENDWISE_SEED_DEMO", "true").lower() not in ("false", "0", "no", "off")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Create and return a SQLite3 connection with row factory configured as sqlite3.Row.
    """
    target_path = db_path or DB_PATH
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """
    Create the `transactions` and `budgets` tables if they do not exist,
    and populate initial demo records if the database is empty.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Create transactions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            merchant TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT DEFAULT '',
            source TEXT DEFAULT 'Text',
            created_at TEXT NOT NULL
        )
        """
    )

    # 2. Create budgets table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            monthly_budget REAL NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            UNIQUE(category, month, year)
        )
        """
    )

    conn.commit()
    if seed_demo_enabled():
        _seed_initial_data_if_empty(conn)
    conn.close()


def _demo_date(days_ago: int, current_period: bool) -> str:
    """
    A demo date `days_ago` days before today (DD-MM-YYYY). "This week / this month" rows
    are kept inside the current month, so the monthly demo totals are always visible.
    """
    today = date.today()
    day = today - timedelta(days=days_ago)
    if current_period:
        day = max(day, today.replace(day=1))
    return day.strftime("%d-%m-%Y")


def _seed_initial_data_if_empty(conn: sqlite3.Connection) -> None:
    """
    Populate demo budgets (for the current month) and demo transactions (relative to today)
    if the tables are empty. Designed to demonstrate:
    - Shopping exceeding its budget by ₹2,100 this month (Spent: ₹6,100 vs Budget: ₹4,000)
    - A weekly Food spending spike (previous 7 days: ₹1,500 vs last 7 days: ₹3,000)
    """
    cursor = conn.cursor()
    today = date.today()

    cursor.execute("SELECT COUNT(*) as cnt FROM budgets")
    if cursor.fetchone()["cnt"] == 0:
        default_budgets = [
            ("Food", 5000.0),
            ("Transport", 3000.0),
            ("Shopping", 4000.0),
            ("Entertainment", 2000.0),
            ("Bills", 3500.0),
            ("Healthcare", 1500.0),
            ("Education", 4000.0),
            ("Others", 1500.0),
        ]
        cursor.executemany(
            """
            INSERT INTO budgets (category, monthly_budget, month, year)
            VALUES (?, ?, ?, ?)
            """,
            [(category, amount, today.month, today.year) for category, amount in default_budgets],
        )

    cursor.execute("SELECT COUNT(*) as cnt FROM transactions")
    if cursor.fetchone()["cnt"] == 0:
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # (days ago, merchant, amount, category, description, source)
        previous_week = [  # 7-13 days ago -> Food = ₹1,500
            (12, "Zomato", 420.0, "Food", "Hostel study group snacks", "Text"),
            (10, "Campus Canteen", 380.0, "Food", "Weekly lunch combo", "CSV"),
            (8, "Blinkit", 700.0, "Food", "Groceries & fruits", "CSV"),
            (9, "Delhi Metro", 400.0, "Transport", "Metro smart card recharge", "CSV"),
            (7, "BookMyShow", 450.0, "Entertainment", "Weekend movie ticket", "Text"),
        ]
        this_week = [  # last 7 days -> Food = ₹3,000 (Spike!), Shopping = ₹6,100 (Over Budget by ₹2,100!)
            (6, "Swiggy", 450.0, "Food", "Dinner", "Text"),
            (6, "Uber", 230.0, "Transport", "College", "CSV"),
            (5, "Amazon", 1800.0, "Shopping", "Shoes", "Receipt"),
            (5, "Starbucks", 550.0, "Food", "Coffee & sandwich with team", "Receipt"),
            (4, "Myntra", 2400.0, "Shopping", "Winter jacket & apparel", "CSV"),
            (4, "Airtel", 899.0, "Bills", "Fiber broadband & mobile plan", "CSV"),
            (3, "Barbeque Nation", 1250.0, "Food", "Birthday dinner buffet", "Receipt"),
            (3, "Rapido", 320.0, "Transport", "Lab commute rides", "Text"),
            (2, "Croma", 1900.0, "Shopping", "Wireless keyboard & mouse", "Receipt"),
            (2, "Blue Tokai", 750.0, "Food", "Artisan coffee & bakery", "Text"),
            (1, "Spotify", 119.0, "Entertainment", "Student premium subscription", "CSV"),
            (1, "Apollo Pharmacy", 480.0, "Healthcare", "Vitamins & first aid", "Receipt"),
            (1, "Coursera", 1450.0, "Education", "ML Specialization certificate", "CSV"),
            (0, "BESCOM", 1350.0, "Bills", "Monthly electricity bill", "CSV"),
            (0, "Crossword", 390.0, "Others", "Stationery & notebooks", "Text"),
        ]
        seed_transactions = [
            (_demo_date(days, current_period=False), merchant, amount, category, description, source, now_iso)
            for days, merchant, amount, category, description, source in previous_week
        ] + [
            (_demo_date(days, current_period=True), merchant, amount, category, description, source, now_iso)
            for days, merchant, amount, category, description, source in this_week
        ]
        cursor.executemany(
            """
            INSERT INTO transactions (date, merchant, amount, category, description, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            seed_transactions,
        )

    conn.commit()
