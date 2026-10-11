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
    add_expense.invoke({"merchant": "Recent Cafe", "amount": 90, "category": "Food", "date": "11-10-2026"})
    add_expense.invoke({"merchant": "Old Import Cafe", "amount": 70, "category": "Food", "date": "01-09-2026"})

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
