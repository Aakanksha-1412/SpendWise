"""CSV import: realistic, messy bank/UPI files."""

from pathlib import Path

import database.database as database
from tools.csv_import_tool import import_rows, read_transactions_csv
from tools.database_tool import get_transactions

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_transactions.csv"


def _fresh():
    database.init_db()
    from tools.database_tool import remove_all_data, save_profile

    save_profile(20000, 0, {})
    remove_all_data()


def test_sample_file_imports_all_rows():
    _fresh()
    result = read_transactions_csv(SAMPLE.read_bytes())

    assert result["error"] is None and len(result["rows"]) == 15
    assert import_rows(result["rows"])["imported"] == 15


def test_missing_columns_give_a_clear_error():
    result = read_transactions_csv(b"day,shop,price\n10-10-2026,X,10\n")

    assert "date, merchant, amount" in result["error"]


def test_amounts_with_commas_and_rupee_signs_are_read():
    _fresh()
    csv = 'date,merchant,amount\n08-10-2026,Croma,"1,200"\n08-10-2026,Zara,"₹2,499.50"\n08-10-2026,Ola,Rs 300\n'

    result = read_transactions_csv(csv.encode("utf-8"))

    assert [row["amount"] for row in result["rows"]] == [1200.0, 2499.5, 300.0]


def test_a_broken_line_is_skipped_and_the_rest_still_imports():
    _fresh()
    csv = "date,merchant,amount\n08-10-2026,Zara,₹2,499.50\n08-10-2026,Ola,300\n"  # line 2 has an extra comma

    result = read_transactions_csv(csv.encode("utf-8"))

    assert [row["merchant"] for row in result["rows"]] == ["Ola"]
    assert any("columns" in reason for reason in result["skipped"])


def test_blank_cells_are_not_saved_as_nan_and_blank_category_is_worked_out():
    _fresh()
    csv = "date,merchant,amount,description,category\n07-10-2026,,300,,\n07-10-2026,Swiggy,200,dinner,\n"

    rows = read_transactions_csv(csv.encode("utf-8"))["rows"]

    assert rows[0]["merchant"] == "Unknown" and rows[0]["description"] == ""
    assert rows[1]["category"] == "Food"
    assert "nan" not in str(rows).lower()


def test_refunds_and_bad_rows_are_skipped_with_a_reason_and_nothing_half_saved():
    _fresh()
    csv = "date,merchant,amount\n06-10-2026,Swiggy,250\n06-10-2026,Amazon refund,-500\n31-02-2026,Uber,100\nnot-a-date,Ola,90\n06-10-2026,Rapido,abc\n"

    result = read_transactions_csv(csv.encode("utf-8"))

    assert [row["merchant"] for row in result["rows"]] == ["Swiggy"]
    assert len(result["skipped"]) == 4
    assert any("refund" in reason.lower() or "credit" in reason.lower() for reason in result["skipped"])


def test_importing_the_same_file_twice_does_not_duplicate():
    _fresh()
    rows = read_transactions_csv(SAMPLE.read_bytes())["rows"]
    import_rows(rows)

    second = import_rows(rows)

    assert second == {"imported": 0, "duplicates": 15}
    assert len(get_transactions()) == 15


def test_future_dated_rows_are_skipped_and_the_rest_still_imports():
    from datetime import date, timedelta

    tomorrow = (date.today() + timedelta(days=1)).strftime("%d-%m-%Y")
    today = date.today().strftime("%d-%m-%Y")
    csv = f"date,merchant,amount\n{today},Swiggy,450\n{tomorrow},Future Store,999\n"

    result = read_transactions_csv(csv.encode("utf-8"))

    assert [row["merchant"] for row in result["rows"]] == ["Swiggy"]
    assert result["skipped"] == [f"row 3: the date {tomorrow} is in the future"]


def test_credits_are_skipped_as_money_received():
    _fresh()
    csv = (
        "date,merchant,amount,type\n10-10-2026,Salary ACME,50000,CR\n10-10-2026,Swiggy,450,DR\n"
        "10-10-2026,Amazon,500 CR,\n10-10-2026,Uber,300.00 Dr,\n"
    )

    result = read_transactions_csv(csv.encode("utf-8"))

    assert [(row["merchant"], row["amount"]) for row in result["rows"]] == [("Swiggy", 450.0), ("Uber", 300.0)]
    assert result["skipped"] == [
        "row 2: this is money received (credit), not an expense",
        "row 4: this is money received (credit), not an expense",
    ]


def test_indian_bank_date_formats_are_read():
    _fresh()
    csv = "date,merchant,amount\n25 Oct 2025,Swiggy,450\n25-Oct-2025,Zomato,300\n25/10/25,Uber,200\n24-10-25,Ola,100\n"

    result = read_transactions_csv(csv.encode("utf-8"))

    assert [row["date"] for row in result["rows"]] == ["25-10-2025", "25-10-2025", "25-10-2025", "24-10-2025"]
    assert result["skipped"] == []


def test_two_real_purchases_in_one_file_are_both_kept_but_a_reimport_adds_nothing():
    _fresh()
    rows = read_transactions_csv(b"date,merchant,amount\n20-10-2025,Tea Stall,20\n20-10-2025,Tea Stall,20\n")["rows"]

    assert import_rows(rows) == {"imported": 2, "duplicates": 0}
    assert import_rows(rows) == {"imported": 0, "duplicates": 2}
    assert len(get_transactions()) == 2


def test_nan_amount_is_skipped_and_nothing_crashes():
    _fresh()
    result = read_transactions_csv(b"date,merchant,amount\n20-10-2025,Chai,30\n20-10-2025,Snacks,nan\n20-10-2025,Juice,inf\n")

    assert [row["merchant"] for row in result["rows"]] == ["Chai"]
    assert result["skipped"] == ["row 3: amount 'nan' is not a number", "row 4: amount 'inf' is not a number"]
    assert import_rows(result["rows"])["imported"] == 1
    assert import_rows(read_transactions_csv(b"date,merchant,amount\n21-10-2025,Tea,20\n")["rows"])["imported"] == 1


def test_a_failing_import_saves_nothing():
    from tools.database_tool import bulk_insert_transactions

    _fresh()
    good = {"date": "20-10-2025", "merchant": "Chai", "amount": 30, "category": "Food"}
    bad = {"date": "20-10-2025", "merchant": "Broken", "amount": float("nan"), "category": "Food"}

    try:
        bulk_insert_transactions([good, bad])
    except Exception:
        pass

    assert get_transactions() == []  # all or nothing
    assert bulk_insert_transactions([good]) == 1  # and the database is not left locked
