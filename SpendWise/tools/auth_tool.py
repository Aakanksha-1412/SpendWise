"""
SpendWise — Accounts & Login Tool
=================================
Owner: Member 2 (Database + Categorization)

Responsibility:
- Sign up and log in with a username + password.
- Passwords are NEVER stored: only a salted PBKDF2-SHA256 hash (Python standard library),
  so even someone who opens the database file can't read them.
- A new account can start with demo data, or take over the data that was already on
  this computer from before login existed (user 0).
- "Stay logged in" across page refreshes: a random login key kept in a browser cookie
  (only its hash is stored); logging out deletes it.
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, Union

from database.database import NO_LOGIN_USER, get_connection, init_db, seed_demo_data

PASSWORD_HASH_ITERATIONS = 200_000
MIN_PASSWORD_LENGTH = 6
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.]{3,30}$")


def _hash_password(password: str, salt_hex: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), PASSWORD_HASH_ITERATIONS)
    return digest.hex()


def create_user(
    username: str,
    password: str,
    with_demo_data: bool = False,
    claim_existing_data: bool = False,
) -> Tuple[bool, Union[int, str]]:
    """
    Create an account. Returns (True, user_id) or (False, "reason for the user").
    - with_demo_data: give the new account the demo expenses/budgets to explore.
    - claim_existing_data: move the data saved without login (user 0) into this account.
    """
    username = (username or "").strip()
    if not USERNAME_PATTERN.match(username):
        return False, "Username: 3-30 letters, numbers, '_' or '.' (no spaces)."
    if len(password or "") < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    init_db(allow_demo=False)
    conn = get_connection()
    if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        conn.close()
        return False, "That username is already taken."

    salt = secrets.token_hex(16)
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
        (username, _hash_password(password, salt), salt, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    user_id = cursor.lastrowid
    if claim_existing_data:
        for table in ("transactions", "budgets", "profile", "usual_spending"):
            conn.execute(f"UPDATE {table} SET user_id = ? WHERE user_id = ?", (user_id, NO_LOGIN_USER))
    conn.commit()
    if with_demo_data:
        seed_demo_data(conn, user_id)
    conn.close()
    return True, user_id


def verify_user(username: str, password: str) -> Optional[int]:
    """The user's id if the username/password are correct, otherwise None."""
    init_db(allow_demo=False)
    conn = get_connection()
    row = conn.execute(
        "SELECT id, password_hash, salt FROM users WHERE username = ?", ((username or "").strip(),)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    if not hmac.compare_digest(_hash_password(password or "", row["salt"]), row["password_hash"]):
        return None
    return int(row["id"])


# "Stay logged in": the browser keeps a random key in a cookie; only its SHA-256 hash is
# stored here, so the database file alone can't be used to log in.
LOGIN_COOKIE = "sw_session"
LOGIN_DAYS = 7


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_login_token(user_id: int) -> str:
    """A new random login key for this user, valid for LOGIN_DAYS days."""
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(days=LOGIN_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    init_db(allow_demo=False)
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM login_sessions WHERE expires_at < ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
            conn.execute(
                "INSERT INTO login_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (_token_hash(token), int(user_id), expires),
            )
    finally:
        conn.close()
    return token


def user_for_login_token(token: str) -> Optional[Tuple[int, str]]:
    """(user_id, username) for a valid, unexpired login key, otherwise None."""
    if not token:
        return None
    init_db(allow_demo=False)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT users.id, users.username FROM login_sessions JOIN users ON users.id = login_sessions.user_id "
            "WHERE login_sessions.token_hash = ? AND login_sessions.expires_at >= ?",
            (_token_hash(token), datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ).fetchone()
    finally:
        conn.close()
    return (int(row["id"]), row["username"]) if row else None


def delete_login_token(token: str) -> None:
    """Log out: the key stops working immediately."""
    if not token:
        return
    init_db(allow_demo=False)
    conn = get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM login_sessions WHERE token_hash = ?", (_token_hash(token),))
    finally:
        conn.close()


def unowned_data_summary() -> str:
    """Plain-language list of the data saved without login, e.g. "20 expenses, 8 budgets, a profile"."""
    init_db(allow_demo=False)
    conn = get_connection()
    expenses = conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id = ?", (NO_LOGIN_USER,)).fetchone()[0]
    budgets = conn.execute("SELECT COUNT(*) FROM budgets WHERE user_id = ?", (NO_LOGIN_USER,)).fetchone()[0]
    profile = conn.execute("SELECT COUNT(*) FROM profile WHERE user_id = ?", (NO_LOGIN_USER,)).fetchone()[0]
    conn.close()
    parts = [f"{expenses} expenses", f"{budgets} budgets"] + (["a profile (income & savings goal)"] if profile else [])
    return ", ".join(parts)


def has_unowned_data() -> bool:
    """True if this computer has data saved before login existed (shown as an option at sign-up)."""
    init_db(allow_demo=False)
    conn = get_connection()
    count = conn.execute(
        "SELECT (SELECT COUNT(*) FROM transactions WHERE user_id = ?) + (SELECT COUNT(*) FROM profile WHERE user_id = ?)",
        (NO_LOGIN_USER, NO_LOGIN_USER),
    ).fetchone()[0]
    conn.close()
    return count > 0
