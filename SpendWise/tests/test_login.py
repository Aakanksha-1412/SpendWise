"""Login: accounts, password safety, and each user seeing only their own data."""

import sqlite3

import database.database as database
from database.database import set_current_user
from tools.auth_tool import create_user, verify_user
from tools.database_tool import (
    add_transaction,
    get_all_budgets,
    get_profile,
    get_transactions,
    save_profile,
    upsert_budget,
)


def test_sign_up_then_log_in_with_the_right_password_only():
    ok, user_id = create_user("asha", "secret123")

    assert ok
    assert verify_user("asha", "secret123") == user_id
    assert verify_user("ASHA", "secret123") == user_id  # usernames ignore capital letters
    assert verify_user("asha", "wrong-password") is None
    assert verify_user("nobody", "secret123") is None


def test_password_is_never_stored_as_plain_text():
    create_user("ravi", "mypassword1")

    conn = sqlite3.connect(database.DB_PATH)
    stored = conn.execute("SELECT * FROM users WHERE username = 'ravi'").fetchone()
    conn.close()

    assert "mypassword1" not in str(stored)


def test_username_must_be_unique_and_password_long_enough():
    assert create_user("asha", "secret123")[0]
    assert create_user("Asha", "another123") == (False, "That username is already taken.")
    assert create_user("bob", "123")[0] is False


def test_each_user_sees_only_their_own_expenses_budgets_and_profile():
    _, asha = create_user("asha", "secret123")
    _, ravi = create_user("ravi", "secret456")

    set_current_user(asha)
    add_transaction({"merchant": "Swiggy", "amount": 300, "category": "Food", "date": ""})
    upsert_budget("Food", 4000)
    save_profile(20000, 3000, {"Food": 4000})

    set_current_user(ravi)
    assert get_transactions() == []
    assert get_all_budgets()["Food"] == 0.0
    assert get_profile() is None

    set_current_user(asha)
    assert [t["merchant"] for t in get_transactions()] == ["Swiggy"]
    assert get_all_budgets()["Food"] == 4000.0
    assert get_profile()["monthly_income"] == 20000


def test_new_account_can_start_with_demo_data():
    _, user_id = create_user("demo_user", "secret123", with_demo_data=True)

    set_current_user(user_id)

    assert len(get_transactions()) > 10
    assert get_all_budgets()["Shopping"] == 4000.0


def test_new_account_can_take_over_the_data_already_on_this_computer():
    database.init_db()  # data from before login existed (demo data, no owner)
    before = len(get_transactions())

    _, user_id = create_user("owner", "secret123", claim_existing_data=True)
    set_current_user(user_id)

    assert len(get_transactions()) == before


def test_an_old_database_without_users_is_upgraded_and_keeps_its_data(tmp_path, monkeypatch):
    old_db = tmp_path / "old.db"
    conn = sqlite3.connect(old_db)
    conn.executescript(
        """
        CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, merchant TEXT NOT NULL,
            amount REAL NOT NULL, category TEXT NOT NULL, description TEXT DEFAULT '', source TEXT DEFAULT 'Text',
            created_at TEXT NOT NULL);
        CREATE TABLE budgets (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, monthly_budget REAL NOT NULL,
            month INTEGER NOT NULL, year INTEGER NOT NULL, UNIQUE(category, month, year));
        CREATE TABLE profile (id INTEGER PRIMARY KEY CHECK (id = 1), monthly_income REAL NOT NULL,
            savings_goal REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
        CREATE TABLE usual_spending (category TEXT PRIMARY KEY, amount REAL NOT NULL);
        INSERT INTO transactions (date, merchant, amount, category, created_at) VALUES ('05-10-2026', 'Zomato', 250, 'Food', 'x');
        INSERT INTO budgets (category, monthly_budget, month, year) VALUES ('Food', 4500, 10, 2026);
        INSERT INTO profile (id, monthly_income, savings_goal, updated_at) VALUES (1, 18000, 2000, 'x');
        INSERT INTO usual_spending (category, amount) VALUES ('Food', 3500);
        """
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(database, "DB_PATH", str(old_db))

    database.init_db()

    assert [t["merchant"] for t in get_transactions()] == ["Zomato"]
    assert get_all_budgets(month=10, year=2026)["Food"] == 4500.0
    assert get_profile()["monthly_income"] == 18000
    assert get_profile()["usual_spending"]["Food"] == 3500


def test_shops_learned_by_one_user_are_not_used_for_another():
    from tools.categorization_tool import categorize_expense

    _, asha = create_user("asha", "secret123")
    _, ravi = create_user("ravi", "secret456")

    set_current_user(asha)
    add_transaction({"merchant": "Plinkerton Hub", "amount": 500, "category": "Education", "date": ""})
    assert categorize_expense("Plinkerton Hub") == "Education"

    set_current_user(ravi)
    assert categorize_expense("Plinkerton Hub") == "Others"
