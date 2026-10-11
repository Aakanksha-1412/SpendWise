"""Member 3: budget status and rolling-week spike detection."""

from freezegun import freeze_time

import database.database as database
from tools.budget_tool import calculate_budget_status
from tools.database_tool import add_transaction
from tools.spike_detector import detect_spending_spike


def test_category_without_budget_is_not_called_over_budget(monkeypatch):
    monkeypatch.setenv("SPENDWISE_SEED_DEMO", "false")
    database.init_db()
    add_transaction({"merchant": "Swiggy", "amount": 300, "category": "Food", "date": ""})

    assert calculate_budget_status("Food")["status"] == "NO BUDGET SET"


def test_spike_compares_the_last_7_days_with_the_7_days_before(monkeypatch):
    monkeypatch.setenv("SPENDWISE_SEED_DEMO", "false")
    with freeze_time("2027-01-20"):
        database.init_db()
        add_transaction({"merchant": "Swiggy", "amount": 500, "category": "Food", "date": "10-01-2027"})  # previous week
        add_transaction({"merchant": "Swiggy", "amount": 1500, "category": "Food", "date": "18-01-2027"})  # this week
        add_transaction({"merchant": "Swiggy", "amount": 9999, "category": "Food", "date": "01-01-2027"})  # too old

        spike = detect_spending_spike("Food")

    assert spike["previous_weekly_spending"] == 500.0
    assert spike["current_weekly_spending"] == 1500.0
    assert spike["spike_detected"] is True


def test_demo_data_shows_the_food_spike_on_any_date():
    with freeze_time("2027-06-15"):
        database.init_db()
        spike = detect_spending_spike("Food")

    assert spike["previous_weekly_spending"] == 1500.0
    assert spike["current_weekly_spending"] == 3000.0
    assert spike["spike_detected"] is True


def test_overview_matches_each_single_category_status():
    from tools.budget_tool import get_all_budget_statuses

    database.init_db()
    add_transaction({"merchant": "Zomato", "amount": 250, "category": "Food", "date": ""})

    overview = {status["category"]: status for status in get_all_budget_statuses()}

    for category, status in overview.items():
        assert status == calculate_budget_status(category)
