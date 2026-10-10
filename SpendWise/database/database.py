"""
SpendWise — SQLite Database Connection & Initialization
=======================================================
Owner: Member 2 (Database + Categorization)

Responsibility:
- Manages the SQLite3 database connection (`spendwise.db`).
- Initializes the required tables (`transactions` and `budgets`).
- Seeds realistic initial demo data on first run so the dashboard and analytics
  work out-of-the-box for all team members.
- NOTE: UI pages (`pages/*.py`) must NEVER write raw SQL queries directly.
  All reads/writes go through `tools/database_tool.py`.
"""

import os
import sqlite3
from datetime import datetime
from typing import Optional

DB_PATH = os.getenv(
    "SPENDWISE_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "spendwise.db"),
)


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
    _seed_initial_data_if_empty(conn)
    conn.close()


def _seed_initial_data_if_empty(conn: sqlite3.Connection) -> None:
    """
    Populate initial demo budgets and transactions for October 2026 if tables are empty.
    Designed to demonstrate:
    - Shopping exceeding budget by ₹2,100 (Spent: ₹6,100 vs Budget: ₹4,000)
    - Weekly Food spending spike (Previous week: ₹1,500 vs Current week: ₹3,000)
    """
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM budgets")
    if cursor.fetchone()["cnt"] == 0:
        default_budgets = [
            ("Food", 5000.0, 10, 2026),
            ("Transport", 3000.0, 10, 2026),
            ("Shopping", 4000.0, 10, 2026),
            ("Entertainment", 2000.0, 10, 2026),
            ("Bills", 3500.0, 10, 2026),
            ("Healthcare", 1500.0, 10, 2026),
            ("Education", 4000.0, 10, 2026),
            ("Others", 1500.0, 10, 2026),
        ]
        cursor.executemany(
            """
            INSERT INTO budgets (category, monthly_budget, month, year)
            VALUES (?, ?, ?, ?)
            """,
            default_budgets,
        )

    cursor.execute("SELECT COUNT(*) as cnt FROM transactions")
    if cursor.fetchone()["cnt"] == 0:
        now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        seed_transactions = [
            # Previous week transactions (2026-09-18 to 2026-09-24) -> Food = ₹1,500
            ("19-09-2026", "Zomato", 420.0, "Food", "Hostel study group snacks", "Text", now_iso),
            ("21-09-2026", "Campus Canteen", 380.0, "Food", "Weekly lunch combo", "CSV", now_iso),
            ("23-09-2026", "Blinkit", 700.0, "Food", "Groceries & fruits", "CSV", now_iso),
            ("22-09-2026", "Delhi Metro", 400.0, "Transport", "Metro smart card recharge", "CSV", now_iso),
            ("24-09-2026", "BookMyShow", 450.0, "Entertainment", "Weekend movie ticket", "Text", now_iso),

            # Current week / Month transactions (October 2026) -> Food = ₹3,000 (Spike!), Shopping = ₹6,100 (Over Budget by ₹2,100!)
            ("01-10-2026", "Swiggy", 450.0, "Food", "Dinner", "Text", now_iso),
            ("01-10-2026", "Uber", 230.0, "Transport", "College", "CSV", now_iso),
            ("02-10-2026", "Amazon", 1800.0, "Shopping", "Shoes", "Receipt", now_iso),
            ("02-10-2026", "Starbucks", 550.0, "Food", "Coffee & sandwich with team", "Receipt", now_iso),
            ("03-10-2026", "Myntra", 2400.0, "Shopping", "Winter jacket & apparel", "CSV", now_iso),
            ("03-10-2026", "Airtel", 899.0, "Bills", "Fiber broadband & mobile plan", "CSV", now_iso),
            ("04-10-2026", "Barbeque Nation", 1250.0, "Food", "Birthday dinner buffet", "Receipt", now_iso),
            ("04-10-2026", "Rapido", 320.0, "Transport", "Lab commute rides", "Text", now_iso),
            ("05-10-2026", "Croma", 1900.0, "Shopping", "Wireless keyboard & mouse", "Receipt", now_iso),
            ("05-10-2026", "Blue Tokai", 750.0, "Food", "Artisan coffee & bakery", "Text", now_iso),
            ("06-10-2026", "Spotify", 119.0, "Entertainment", "Student premium subscription", "CSV", now_iso),
            ("06-10-2026", "Apollo Pharmacy", 480.0, "Healthcare", "Vitamins & first aid", "Receipt", now_iso),
            ("07-10-2026", "Coursera", 1450.0, "Education", "ML Specialization certificate", "CSV", now_iso),
            ("07-10-2026", "BESCOM", 1350.0, "Bills", "Monthly electricity bill", "CSV", now_iso),
            ("08-10-2026", "Crossword", 390.0, "Others", "Stationery & notebooks", "Text", now_iso),
        ]
        cursor.executemany(
            """
            INSERT INTO transactions (date, merchant, amount, category, description, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            seed_transactions,
        )

    conn.commit()
