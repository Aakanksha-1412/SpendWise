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
