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
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime
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
