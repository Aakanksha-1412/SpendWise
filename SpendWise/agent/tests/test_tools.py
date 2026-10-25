"""
Seam: the agent tools, called exactly the way Gemini calls them (`tool.invoke({...})`).
"""

from agent.tools_registry import add_expense, check_affordability, current_receipt, read_uploaded_receipt, search_transactions


def test_add_expense_rejects_a_date_it_cannot_read():
    result = add_expense.invoke(
        {"merchant": "Auto", "amount": 80, "category": "Transport", "date": "yesterday"}
    )

    assert result["saved"] is False
    assert "DD-MM-YYYY" in result["error"]
    assert search_transactions.invoke({"merchant": "Auto"}) == []


def test_search_lists_newest_dates_first_even_if_older_rows_were_added_later():
    from datetime import date, timedelta

    _fresh_user_with_profile(income=20000, savings=2000)  # no demo rows newer than ours
    recent = (date.today() - timedelta(days=2)).strftime("%d-%m-%Y")
    older = (date.today() - timedelta(days=40)).strftime("%d-%m-%Y")
    add_expense.invoke({"merchant": "Recent Cafe", "amount": 90, "category": "Food", "date": recent})
    add_expense.invoke({"merchant": "Old Import Cafe", "amount": 70, "category": "Food", "date": older})

    newest = search_transactions.invoke({"category": "Food", "limit": 1})

    assert newest[0]["merchant"] == "Recent Cafe"


def test_unreadable_receipt_gives_gemini_an_error_not_fake_data(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("TESSERACT_CMD_PATH", "")
    monkeypatch.setattr("shutil.which", lambda name: None)
    token = current_receipt.set(b"not-really-an-image")
    try:
        result = read_uploaded_receipt.invoke({})
    finally:
        current_receipt.reset(token)

    assert "error" in result
    assert "merchant" not in result


def test_affordability_with_no_budget_set_does_not_say_over_budget(monkeypatch):
    from tools.database_tool import upsert_budget

    upsert_budget("Healthcare", 0.0)  # user removed the Healthcare budget this month

    result = check_affordability.invoke({"category": "Healthcare", "amount": 200})

    assert result["can_afford"] is None
    assert result["no_budget_set"] is True


def test_profile_tool_tells_gemini_income_and_savings():
    from agent.tools_registry import get_my_profile
    from tools.database_tool import save_profile

    assert "error" in get_my_profile.invoke({})  # no profile yet

    save_profile(monthly_income=20000, savings_goal=3000, usual_spending={"Food": 4000})
    result = get_my_profile.invoke({})

    assert result["monthly_income"] == 20000
    assert result["savings_goal"] == 3000
    assert "left_after_spending" in result


def _fresh_user_with_profile(income, savings):
    from tools.database_tool import remove_all_data, save_profile

    save_profile(monthly_income=income, savings_goal=savings, usual_spending={})
    remove_all_data()


def test_adding_an_expense_reports_when_it_eats_into_the_savings_goal():
    _fresh_user_with_profile(income=10000, savings=3000)
    add_expense.invoke({"merchant": "Myntra", "amount": 6500, "category": "Shopping"})

    result = add_expense.invoke({"merchant": "Croma", "amount": 900, "category": "Shopping"})

    savings = result["savings_after_saving"]
    assert savings["left_after_spending"] == 2600  # 10,000 - 7,400
    assert savings["below_savings_goal_by"] == 400  # goal 3,000
    assert savings["savings_goal_at_risk"] is True


def test_chat_can_set_a_budget():
    from agent.tools_registry import set_budget
    from tools.database_tool import get_all_budgets

    result = set_budget.invoke({"category": "food", "amount": 5000})

    assert result["saved"] is True
    assert get_all_budgets()["Food"] == 5000.0
    assert set_budget.invoke({"category": "Food", "amount": -10})["saved"] is False


def test_chat_can_update_income_and_savings_goal():
    from agent.tools_registry import update_my_profile
    from tools.database_tool import get_profile

    _fresh_user_with_profile(income=10000, savings=2000)

    result = update_my_profile.invoke({"monthly_income": 25000, "savings_goal": 4000})

    assert result["saved"] is True
    assert get_profile()["monthly_income"] == 25000 and get_profile()["savings_goal"] == 4000
    assert update_my_profile.invoke({"savings_goal": 99999})["saved"] is False  # more than income


def test_chat_cannot_budget_more_than_income_minus_savings():
    from agent.tools_registry import set_budget, update_my_profile
    from tools.database_tool import get_all_budgets

    _fresh_user_with_profile(income=10000, savings=2000)
    assert set_budget.invoke({"category": "Food", "amount": 6000})["saved"] is True

    result = set_budget.invoke({"category": "Shopping", "amount": 3000})  # 9,000 > 8,000 allowed

    assert result["saved"] is False and "you can only plan ₹8,000" in result["error"]
    assert get_all_budgets()["Shopping"] == 0.0
    assert update_my_profile.invoke({"monthly_income": 7000})["saved"] is False  # 6,000 > 5,000 allowed


def test_affordability_says_no_when_it_would_cut_into_the_savings_goal():
    from agent.tools_registry import check_affordability
    from tools.database_tool import upsert_budget

    _fresh_user_with_profile(income=200000, savings=50000)
    upsert_budget("Education", 450000)  # saved before budgets were limited to the income
    add_expense.invoke({"merchant": "Swiggy", "amount": 11400, "category": "Food"})

    too_much = check_affordability.invoke({"category": "Education", "amount": 200000})
    eats_savings = check_affordability.invoke({"category": "Education", "amount": 150000})
    fits = check_affordability.invoke({"category": "Education", "amount": 30000})

    assert too_much["can_afford"] is False and too_much["savings_goal_at_risk"] is True
    assert "₹2,00,000 is more than all the money you have left this month (₹1,88,600)" in too_much["answer"]
    assert eats_savings["can_afford"] is False
    assert "would cut into your savings by ₹11,400" in eats_savings["answer"]
    assert fits["can_afford"] is True and fits["remaining_after"] == 420000


def test_chat_cannot_add_an_expense_dated_in_the_future():
    from datetime import date, timedelta
    from tools.database_tool import get_transactions

    _fresh_user_with_profile(income=20000, savings=2000)
    tomorrow = (date.today() + timedelta(days=1)).strftime("%d-%m-%Y")

    result = add_expense.invoke({"merchant": "Future Store", "amount": 999, "category": "Shopping", "date": tomorrow})

    assert result["saved"] is False and "is in the future" in result["error"]
    assert get_transactions() == []
