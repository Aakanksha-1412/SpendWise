"""Member 2: keyword + ChromaDB semantic categorization."""

import database.database as database
from tools.categorization_tool import categorize_expense
from tools.database_tool import add_transaction, bulk_insert_transactions


def test_known_keyword_merchant():
    assert categorize_expense("Swiggy") == "Food"


def test_unknown_but_meaningful_merchant_is_found_by_meaning():
    assert categorize_expense("Chai Point") == "Food"
    assert categorize_expense("Lenskart glasses") == "Shopping"


def test_meaningless_name_stays_others():
    assert categorize_expense("XYZ Traders") == "Others"


def test_learns_a_merchant_after_it_is_saved_once():
    database.init_db()
    add_transaction({"merchant": "Zorblax Learning", "amount": 999, "category": "Education", "date": ""})

    assert categorize_expense("Zorblax Learning") == "Education"


def test_college_fees_are_education_not_transport():
    assert categorize_expense("", "Paid college fees 50000") == "Education"
    assert categorize_expense("Uber", "ride to college") == "Transport"


def test_csv_import_teaches_merchants_too():
    database.init_db()
    bulk_insert_transactions([
        {"merchant": "Quixotic Tutors", "amount": 500, "category": "Education", "date": ""},
        {"merchant": "Wobbly Pans", "amount": 200, "category": "Food", "date": ""},
    ])

    assert categorize_expense("Quixotic Tutors") == "Education"
    assert categorize_expense("Wobbly Pans") == "Food"


def test_typed_expense_without_a_shop_name_is_not_guessed_as_shopping():
    from tools.categorization_tool import parse_natural_language_expense

    assert parse_natural_language_expense("spent 200 yesterday")["category"] == "Others"
    assert parse_natural_language_expense("paid 150")["category"] == "Others"


def test_keyword_only_mode_skips_chromadb():
    assert categorize_expense("Chai Point", use_semantic=False) == "Others"
    assert categorize_expense("Swiggy", use_semantic=False) == "Food"


def test_memory_version_changes_when_a_merchant_is_learned():
    from tools.categorization_tool import merchant_memory_version, remember_merchant_category

    before = merchant_memory_version()
    remember_merchant_category("Fizzwick Books", "Education")

    assert merchant_memory_version() > before


def test_a_learned_shop_name_does_not_pull_in_unrelated_names():
    from tools.categorization_tool import remember_merchant_category

    remember_merchant_category("Zomato", "Food")
    remember_merchant_category("Wobbly Pans", "Food")

    assert categorize_expense("XYZ Traders") == "Others"
    assert categorize_expense("Sharma Enterprises") == "Others"


def test_a_learned_shop_matches_small_spelling_differences():
    from tools.categorization_tool import remember_merchant_category

    remember_merchant_category("Quillfeather Academy", "Education")

    assert categorize_expense("Quillfeather academy") == "Education"


def test_typed_amount_is_the_price_not_the_quantity():
    from tools.categorization_tool import parse_natural_language_expense

    assert parse_natural_language_expense("bought 2 coffees for 300 at Starbucks")["amount"] == 300.0
    assert parse_natural_language_expense("paid 1,200 for 3 movie tickets at PVR")["amount"] == 1200.0
    assert parse_natural_language_expense("Uber 230 to college")["amount"] == 230.0


def test_yesterday_and_today_are_understood():
    from freezegun import freeze_time
    from tools.categorization_tool import parse_natural_language_expense

    with freeze_time("2026-11-01"):
        assert parse_natural_language_expense("spent 450 on Swiggy yesterday")["date"] == "31-10-2026"
        assert parse_natural_language_expense("spent 450 on Swiggy today")["date"] == "01-11-2026"


def test_typed_entry_reads_dates_and_amounts_correctly():
    from tools.categorization_tool import parse_natural_language_expense as parse

    assert parse("Swiggy dinner on 01-10-2026")["amount"] == 0.0  # the date is not the amount
    assert parse("Spent ₹1,25,000 at Croma for a laptop")["amount"] == 125000.0  # Indian commas
    assert parse("Spent ₹125,000 at Croma")["amount"] == 125000.0  # Western commas still work
    slash = parse("Spent 300 at Uber on 25/09/2026")
    assert slash["date"] == "25-09-2026" and slash["amount"] == 300.0
    assert parse("Spent 450 at Swiggy on 01-10-2026")["amount"] == 450.0


def test_money_received_is_recognised():
    from tools.categorization_tool import parse_natural_language_expense as parse

    assert parse("Got refund of 500 from Amazon")["looks_like_income"] is True
    assert parse("Received 2000 from Rahul")["looks_like_income"] is True
    assert parse("Salary credited 50000")["looks_like_income"] is True
    assert parse("Spent 450 at Swiggy")["looks_like_income"] is False
