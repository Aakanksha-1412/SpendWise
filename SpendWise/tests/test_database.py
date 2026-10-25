"""Member 2: database setup, demo data switch, budgets per month."""

from freezegun import freeze_time

import database.database as database
from tools.budget_tool import calculate_budget_status
from tools.database_tool import get_all_budgets, get_transactions, upsert_budget


def test_demo_switch_off_starts_with_empty_tables(monkeypatch):
    monkeypatch.setenv("SPENDWISE_SEED_DEMO", "false")
    database.init_db()

    assert get_transactions() == []
    assert set(get_all_budgets().values()) == {0.0}


def test_demo_data_shows_the_shopping_alert_in_any_month():
    with freeze_time("2027-03-20"):
        database.init_db()
        shopping = calculate_budget_status("Shopping")

    assert shopping["spent"] == 6100.0
    assert shopping["remaining"] == -2100.0
    assert shopping["status"] == "OVER BUDGET"


def test_last_months_budgets_carry_over_into_a_new_month():
    with freeze_time("2026-10-11"):
        database.init_db()
    with freeze_time("2026-11-02"):
        assert get_all_budgets()["Food"] == 5000.0


def test_saving_a_budget_uses_the_current_month():
    with freeze_time("2026-10-11"):
        database.init_db()
    with freeze_time("2026-12-05"):
        upsert_budget("Food", 7000.0)
        assert get_all_budgets()["Food"] == 7000.0
    with freeze_time("2026-10-11"):
        assert get_all_budgets()["Food"] == 5000.0  # October unchanged


def test_category_spelling_from_a_csv_is_accepted_in_any_case():
    from tools.database_tool import bulk_insert_transactions

    database.init_db()
    bulk_insert_transactions([{"date": "", "merchant": "Swiggy", "amount": 200, "category": "food", "description": ""}])

    assert get_transactions(merchant_query="swiggy")[0]["category"] == "Food"


def test_amounts_use_indian_digit_grouping():
    from utils.helpers import format_inr

    assert format_inr(0) == "₹0"
    assert format_inr(999) == "₹999"
    assert format_inr(4500) == "₹4,500"
    assert format_inr(200000) == "₹2,00,000"
    assert format_inr(547500) == "₹5,47,500"
    assert format_inr(1250000) == "₹12,50,000"
    assert format_inr(123456789) == "₹12,34,56,789"
    assert format_inr(1234.5) == "₹1,234.50"
    assert format_inr(-397500) == "-₹3,97,500"
    assert format_inr(2100, include_sign=True) == "+₹2,100"
