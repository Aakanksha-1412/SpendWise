"""User profile: income, savings goal, usual spending, start fresh, suggested budgets."""

import database.database as database
from analytics.analytics import get_summary_metrics
from tools.budget_tool import suggest_budgets
from tools.database_tool import (
    add_transaction,
    get_all_budgets,
    get_profile,
    get_transactions,
    remove_all_data,
    save_profile,
)


def test_no_profile_until_the_user_saves_one():
    database.init_db()

    assert get_profile() is None


def test_profile_is_saved_and_read_back():
    database.init_db()
    save_profile(monthly_income=20000, savings_goal=3000, usual_spending={"Food": 4000, "Transport": 1500})

    profile = get_profile()

    assert profile["monthly_income"] == 20000
    assert profile["savings_goal"] == 3000
    assert profile["usual_spending"]["Food"] == 4000
    assert profile["usual_spending"]["Shopping"] == 0  # every category is present


def test_start_fresh_removes_demo_data_and_it_never_comes_back():
    database.init_db()
    assert get_transactions()  # demo data present

    remove_all_data()
    save_profile(monthly_income=15000, savings_goal=2000, usual_spending={})
    database.init_db()  # runs on every page load

    assert get_transactions() == []
    assert set(get_all_budgets().values()) == {0.0}


def test_budgets_follow_usual_spending_when_it_fits_the_income():
    budgets = suggest_budgets(20000, 3000, {"Food": 4000, "Transport": 1500, "Bills": 2000})

    assert budgets["Food"] == 4000
    assert budgets["Transport"] == 1500
    assert budgets["Bills"] == 2000
    assert budgets["Shopping"] == 0


def test_wants_are_trimmed_first_when_spending_is_more_than_income_minus_savings():
    # income 10,000 - savings 2,000 = 8,000 available; usual spending = 10,000
    usual = {"Bills": 3000, "Transport": 1000, "Food": 3000, "Shopping": 3000}

    budgets = suggest_budgets(10000, 2000, usual)

    assert sum(budgets.values()) <= 8000
    assert budgets["Bills"] == 3000 and budgets["Transport"] == 1000  # needs kept
    assert budgets["Food"] < 3000 and budgets["Shopping"] < 3000  # wants cut


def test_without_usual_spending_the_available_money_is_still_split():
    budgets = suggest_budgets(12000, 2000, {})

    assert 9500 <= sum(budgets.values()) <= 10000
    assert all(amount > 0 for amount in budgets.values())


def test_dashboard_numbers_include_income_and_savings():
    database.init_db()
    remove_all_data()
    save_profile(monthly_income=20000, savings_goal=3000, usual_spending={})
    add_transaction({"merchant": "Swiggy", "amount": 1000, "category": "Food", "date": ""})

    summary = get_summary_metrics()

    assert summary["monthly_income"] == 20000
    assert summary["savings_goal"] == 3000
    assert summary["saved_so_far"] == 19000  # income - spent this month


def test_money_plan_numbers():
    from analytics.analytics import get_money_plan
    from tools.database_tool import upsert_budget

    database.init_db()
    remove_all_data()
    save_profile(monthly_income=20000, savings_goal=3000, usual_spending={})
    upsert_budget("Food", 4000)
    upsert_budget("Shopping", 1000)
    add_transaction({"merchant": "Swiggy", "amount": 3500, "category": "Food", "date": ""})
    add_transaction({"merchant": "Myntra", "amount": 1200, "category": "Shopping", "date": ""})

    plan = get_money_plan()

    assert plan["monthly_income"] == 20000
    assert plan["spent"] == 4700
    assert plan["can_still_spend"] == 12300  # 20,000 - 3,000 savings - 4,700 spent
    assert plan["budget_total"] == 5000
    assert plan["unplanned"] == 12000  # income not given to any budget or savings
    labels = {row["category"]: row["label"] for row in plan["categories"]}
    assert labels["Food"] == "⚠️ almost full"  # 87.5% used
    assert labels["Shopping"] == "🚨 full"  # over budget
    assert labels["Bills"] == "– no budget"


def test_income_split_adds_up_to_the_income():
    from analytics.analytics import get_money_plan
    from tools.database_tool import upsert_budget

    database.init_db()
    remove_all_data()
    save_profile(monthly_income=20000, savings_goal=3000, usual_spending={})
    upsert_budget("Food", 4000)
    upsert_budget("Shopping", 1000)
    add_transaction({"merchant": "Swiggy", "amount": 3500, "category": "Food", "date": ""})
    add_transaction({"merchant": "Myntra", "amount": 1200, "category": "Shopping", "date": ""})

    split = get_money_plan()["income_split"]

    assert split == {"Spent so far": 4700, "Budget left": 500, "Savings goal": 3000, "Not planned yet": 11800}
    assert sum(split.values()) == 20000


def test_savings_slice_is_25_percent_even_with_budgets_saved_above_income():
    from analytics.analytics import get_money_plan
    from tools.database_tool import upsert_budget

    # the numbers from the bug report: income 2,00,000, savings 50,000, budgets 5,47,500
    database.init_db()
    remove_all_data()
    save_profile(monthly_income=200000, savings_goal=50000, usual_spending={})
    for cat, amount in {"Food": 20000, "Transport": 3000, "Shopping": 2500, "Entertainment": 2000,
                        "Bills": 30000, "Healthcare": 40000, "Education": 450000}.items():
        upsert_budget(cat, amount)

    split = get_money_plan()["income_split"]

    assert split["Savings goal"] / 200000 == 0.25
    assert split["Budget left"] == 150000
    assert sum(split.values()) == 200000


def test_no_money_plan_without_a_profile():
    from analytics.analytics import get_money_plan

    database.init_db()

    assert get_money_plan() is None
