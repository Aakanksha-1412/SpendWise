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
