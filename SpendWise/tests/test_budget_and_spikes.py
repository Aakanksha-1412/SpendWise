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


def _fresh_user():
    from tools.database_tool import remove_all_data, save_profile

    database.init_db()
    save_profile(20000, 0, {})
    remove_all_data()


def test_nothing_last_week_has_no_percentage():
    with freeze_time("2027-01-20"):
        _fresh_user()
        add_transaction({"merchant": "Swiggy", "amount": 200, "category": "Food", "date": "01-01-2027"})  # older history
        add_transaction({"merchant": "Swiggy", "amount": 3000, "category": "Food", "date": "18-01-2027"})  # this week

        spike = detect_spending_spike("Food")

    assert spike["increase_pct"] is None and spike["change_label"] == "new"
    assert spike["spike_detected"] is True
    assert spike["message"] == "New Food spending of ₹3,000 this week (nothing in the previous week)."


def test_a_brand_new_category_is_not_called_a_spike():
    with freeze_time("2027-01-20"):
        _fresh_user()
        add_transaction({"merchant": "Myntra", "amount": 3000, "category": "Shopping", "date": "18-01-2027"})

        spike = detect_spending_spike("Shopping")

    assert spike["spike_detected"] is False
    assert "Not enough Shopping history yet" in spike["message"]


def test_small_jumps_from_a_tiny_amount_follow_the_same_rupee_rule():
    with freeze_time("2027-01-20"):
        _fresh_user()
        add_transaction({"merchant": "Chai", "amount": 10, "category": "Food", "date": "10-01-2027"})
        add_transaction({"merchant": "Chai", "amount": 250, "category": "Food", "date": "18-01-2027"})

        spike = detect_spending_spike("Food")

    assert spike["change_label"] == "+2400.0%"
    assert spike["spike_detected"] is False  # only ₹240 more: below the ₹300 rule
