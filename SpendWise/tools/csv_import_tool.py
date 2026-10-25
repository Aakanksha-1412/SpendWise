"""
SpendWise — CSV Statement Import Tool
=====================================
Owner: Member 4 (Streamlit UI + OCR) — ingestion; saves through Member 2's database_tool.

Responsibility:
- Reads a bank / UPI CSV export and cleans every row BEFORE anything is saved:
  amounts like "1,200", "₹2,499.50" or "Rs 300"; dates in common formats; blank cells;
  category names in any case, or worked out automatically when missing/blank.
- Skips rows that aren't expenses or can't be read (refunds/credits by sign, CR/Credit
  type column or "500 CR"; unreadable or future dates; amounts like "nan") and explains
  why, so a bad row never stops the whole import half-way.
- Doesn't save the same expense twice when a file is imported again (repeats inside one
  file are separate purchases and are kept). Saving is all-or-nothing.
- No Streamlit here: `pages/upload.py` shows the preview and calls `import_rows`.
"""

import csv
import io
import math
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional


from tools.categorization_tool import categorize_expense
from tools.database_tool import bulk_insert_transactions, get_transactions
from utils.helpers import CATEGORIES, expense_date_error, normalize_date


REQUIRED_COLUMNS = ("date", "merchant", "amount")
# Columns banks use to say whether money went out (debit) or came in (credit)
TYPE_COLUMNS = ("type", "dr/cr", "cr/dr", "debit/credit", "credit/debit", "transaction type", "txn type")
CREDIT = re.compile(r"^\s*(cr|credit|credited)\b", re.IGNORECASE)
CREDIT_SUFFIX = re.compile(r"\b(cr|credit)\.?\s*$", re.IGNORECASE)


def _parse_amount(text: str) -> Optional[float]:
    """'1,200' / '₹2,499.50' / 'Rs 300' / '(500)' / '500.00 Dr' -> number; None if it isn't one."""
    cleaned = re.sub(r"(?i)₹|\brs\.?|\binr|\bdr\.?\s*$", "", text).replace(",", "").replace(" ", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if not math.isfinite(value):  # "nan", "inf" are not amounts
        return None
    return -value if negative else value


def _is_credit(raw: Dict[str, str]) -> bool:
    """Money coming in: a CR/Credit type column, or an amount like '500 CR'."""
    if CREDIT_SUFFIX.search(str(raw["amount"])):
        return True
    return any(CREDIT.match(str(raw.get(column, ""))) for column in TYPE_COLUMNS)


def read_transactions_csv(data: bytes) -> Dict[str, Any]:
    """
    Read and clean a CSV file's bytes. Returns:
        {"rows": [clean expense dicts], "skipped": ["row 4: ... reason"], "error": None | str}
    """
    text = None
    for encoding in ("utf-8-sig", "cp1252"):  # Excel on Windows often saves as cp1252
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return {"rows": [], "skipped": [], "error": "This file couldn't be read as text (is it really a CSV?)."}

    lines = list(csv.reader(io.StringIO(text)))
    if not lines:
        return {"rows": [], "skipped": [], "error": "The file is empty."}
    header = [column.strip().lower() for column in lines[0]]
    if not set(REQUIRED_COLUMNS).issubset(header):
        return {
            "rows": [],
            "skipped": [],
            "error": "The CSV must have the columns: date, merchant, amount (optional: description, category).",
        }

    official = {cat.lower(): cat for cat in CATEGORIES}
    guessed: Dict[tuple, str] = {}  # each (merchant, description) is categorized only once
    rows: List[Dict[str, Any]] = []
    skipped: List[str] = []

    records = []
    for line_number, cells in enumerate(lines[1:], start=2):  # line 1 is the header
        if not any(cell.strip() for cell in cells):
            continue  # empty line
        if len(cells) != len(header):
            skipped.append(
                f"row {line_number}: has {len(cells)} columns instead of {len(header)} "
                "(put amounts like \"1,200\" in quotes)"
            )
            continue
        records.append((line_number, dict(zip(header, cells))))

    for line, raw in records:
        if _is_credit(raw):
            skipped.append(f"row {line}: this is money received (credit), not an expense")
            continue
        amount = _parse_amount(str(raw["amount"]).strip())
        if amount is None:
            skipped.append(f"row {line}: amount '{raw['amount']}' is not a number")
            continue
        if amount <= 0:
            skipped.append(f"row {line}: {amount:g} looks like a refund/credit, not an expense")
            continue
        date = normalize_date(str(raw["date"]).strip())
        try:
            datetime.strptime(date, "%d-%m-%Y")
        except ValueError:
            skipped.append(f"row {line}: date '{raw['date']}' not understood (use DD-MM-YYYY)")
            continue
        if expense_date_error(date):
            skipped.append(f"row {line}: the date {date} is in the future")
            continue

        merchant = str(raw["merchant"]).strip() or "Unknown"
        description = str(raw.get("description", "")).strip()
        category = official.get(str(raw.get("category", "")).strip().lower())
        if category is None:
            key = ("" if merchant == "Unknown" else merchant, description)
            if key not in guessed:
                guessed[key] = categorize_expense(*key)
            category = guessed[key]

        rows.append(
            {"date": date, "merchant": merchant, "amount": amount, "category": category,
             "description": description, "source": "CSV"}
        )
    return {"rows": rows, "skipped": skipped, "error": None}


def _key(row: Dict[str, Any]) -> tuple:
    return (normalize_date(str(row["date"])), str(row["merchant"]).strip().lower(), round(float(row["amount"]), 2))


def import_rows(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Save cleaned rows, skipping ones already saved in SpendWise (same date, merchant and
    amount). Repeats inside the file are separate purchases (two ₹20 teas) and are kept;
    importing the same file again still saves nothing new.
    """
    already_saved = Counter(_key(existing) for existing in get_transactions())
    new_rows = []
    for row in rows:
        key = _key(row)
        if already_saved[key] > 0:
            already_saved[key] -= 1  # matches one saved expense
        else:
            new_rows.append(row)
    imported = bulk_insert_transactions(new_rows) if new_rows else 0
    return {"imported": imported, "duplicates": len(rows) - len(new_rows)}
