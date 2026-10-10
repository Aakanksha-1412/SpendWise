"""
Seam: the agent tools, called exactly the way Gemini calls them (`tool.invoke({...})`).
"""

from agent.tools_registry import add_expense, search_transactions


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
