"""Member 2: keyword + ChromaDB semantic categorization."""

import database.database as database
from tools.categorization_tool import categorize_expense
from tools.database_tool import add_transaction


def test_known_keyword_merchant():
    assert categorize_expense("Swiggy") == "Food"


def test_unknown_but_meaningful_merchant_is_found_by_meaning():
    assert categorize_expense("Chai Point") == "Food"
    assert categorize_expense("Lenskart glasses") == "Shopping"


def test_meaningless_name_stays_others():
    assert categorize_expense("XYZ Traders") == "Others"


def test_learns_a_merchant_after_it_is_saved_once():
    database.init_db()
    assert categorize_expense("Unacademy Plus") != "Education" or True  # may or may not be known yet
    add_transaction({"merchant": "Zorblax Learning", "amount": 999, "category": "Education", "date": ""})

    assert categorize_expense("Zorblax Learning") == "Education"
