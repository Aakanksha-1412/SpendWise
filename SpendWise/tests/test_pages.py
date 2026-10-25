"""Member 4: every page opens; the assistant keeps question + answer together.
(conftest.py sets GEMINI_API_KEY="" so the assistant runs in demo mode with no Google calls.)"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

# Load the real `analytics` package first: when AppTest runs pages/analytics.py it puts the
# pages/ folder on the import path, and "analytics" could otherwise resolve to that page file.
import analytics.analytics  # noqa: F401

PAGES = Path(__file__).resolve().parents[1] / "pages"


@pytest.mark.parametrize("page", ["home", "transactions", "upload", "budget", "analytics", "assistant", "profile"])
def test_page_opens_without_errors(page):
    app = AppTest.from_file(str(PAGES / f"{page}.py"), default_timeout=60).run()

    assert not app.exception


def test_assistant_shows_question_and_answer():
    app = AppTest.from_file(str(PAGES / "assistant.py"), default_timeout=60).run()
    app.chat_input[0].set_value("how much food budget is left?").run()

    history = app.session_state["chat_history"]
    assert history[-2]["role"] == "user" and history[-2]["content"] == "how much food budget is left?"
    assert history[-1]["role"] == "assistant" and "Food" in history[-1]["content"]


def test_first_setup_saves_income_and_the_budgets_typed_and_removes_demo_data():
    from tools.database_tool import get_all_budgets, get_profile, get_transactions

    app = AppTest.from_file(str(PAGES / "profile.py"), default_timeout=60).run()
    assert get_transactions()  # demo data before setup

    app.number_input(key="profile_income").set_value(20000.0)
    app.number_input(key="profile_savings").set_value(3000.0)
    app.number_input(key="setup_budget_Food").set_value(4000.0)
    app.number_input(key="setup_budget_Bills").set_value(2500.0)
    next(b for b in app.button if b.label == "Save & create my budgets").click().run()  # start fresh ticked

    assert not app.exception
    assert get_profile()["monthly_income"] == 20000.0
    assert get_transactions() == []
    budgets = get_all_budgets()
    assert budgets["Food"] == 4000.0 and budgets["Bills"] == 2500.0 and budgets["Shopping"] == 0.0
    assert any("Saved!" in message.value for message in app.success)
    # after saving: the money plan with charts is shown, the edit form is folded away
    assert any("can still spend" in message.value for message in app.success)
    assert len(app.get("plotly_chart")) == 2
    assert [e.label for e in app.expander] == ["✏️ Edit income & savings goal"]


def test_first_setup_with_empty_budgets_splits_the_money_automatically():
    from tools.database_tool import get_all_budgets

    app = AppTest.from_file(str(PAGES / "profile.py"), default_timeout=60).run()
    app.number_input(key="profile_income").set_value(12000.0)
    app.number_input(key="profile_savings").set_value(2000.0)
    next(b for b in app.button if b.label == "Save & create my budgets").click().run()

    total = sum(get_all_budgets().values())
    assert 9500 <= total <= 10000


def test_home_shows_income_and_savings_after_setup():
    from tools.database_tool import add_transaction, remove_all_data, save_profile

    save_profile(20000, 3000, {})
    remove_all_data()
    add_transaction({"merchant": "Swiggy", "amount": 1000, "category": "Food", "date": ""})

    app = AppTest.from_file(str(PAGES / "home.py"), default_timeout=60).run()

    text = " ".join(m.value for m in app.markdown)
    assert not app.exception
    assert "Income:" in text and "₹20,000" in text and "₹19,000" in text
    assert not any("demo numbers" in i.value for i in app.info)


def test_profile_edit_has_only_income_and_savings_and_keeps_budgets():
    from tools.database_tool import get_all_budgets, get_profile, remove_all_data, save_profile, upsert_budget

    save_profile(15000, 2000, {})
    remove_all_data()
    upsert_budget("Food", 7500)  # set on the Budget page

    app = AppTest.from_file(str(PAGES / "profile.py"), default_timeout=60).run()
    keys = [n.key for n in app.number_input]
    assert keys == ["profile_income", "profile_savings"]  # no per-category amounts here
    app.number_input(key="profile_income").set_value(18000.0)
    next(b for b in app.button if b.label == "Save").click().run()

    assert get_profile()["monthly_income"] == 18000.0
    assert get_all_budgets()["Food"] == 7500.0  # untouched


def test_budget_page_warns_when_budgets_are_more_than_income_minus_savings():
    from tools.database_tool import remove_all_data, save_profile, upsert_budget

    save_profile(10000, 3000, {})
    remove_all_data()
    upsert_budget("Food", 5000)
    upsert_budget("Shopping", 4000)  # 9,000 > 7,000 available

    app = AppTest.from_file(str(PAGES / "budget.py"), default_timeout=60).run()

    assert any("Please lower them by ₹2,000" in w.value for w in app.warning)


def test_budget_page_refuses_budgets_more_than_income_minus_savings():
    from tools.database_tool import get_all_budgets, remove_all_data, save_profile

    save_profile(10000, 3000, {})
    remove_all_data()

    app = AppTest.from_file(str(PAGES / "budget.py"), default_timeout=60).run()
    _budget_input(app, "Food").set_value(5000.0)
    _budget_input(app, "Shopping").set_value(4000.0)  # 9,000 > 7,000 allowed
    next(b for b in app.button if b.label == "Save Monthly Budgets").click().run()

    assert any("You can only budget ₹7,000" in e.value for e in app.error)
    assert sum(get_all_budgets().values()) == 0  # nothing saved


def test_budget_page_saves_budgets_that_fit():
    from tools.database_tool import get_all_budgets, remove_all_data, save_profile

    save_profile(10000, 3000, {})
    remove_all_data()

    app = AppTest.from_file(str(PAGES / "budget.py"), default_timeout=60).run()
    _budget_input(app, "Food").set_value(4000.0)
    _budget_input(app, "Shopping").set_value(3000.0)  # exactly 7,000 is allowed
    next(b for b in app.button if b.label == "Save Monthly Budgets").click().run()

    assert not app.error
    assert get_all_budgets()["Food"] == 4000.0 and get_all_budgets()["Shopping"] == 3000.0


def test_first_setup_refuses_budgets_more_than_income():
    from tools.database_tool import get_profile

    app = AppTest.from_file(str(PAGES / "profile.py"), default_timeout=60).run()
    app.number_input(key="profile_income").set_value(200000.0)
    app.number_input(key="profile_savings").set_value(50000.0)
    app.number_input(key="setup_budget_Education").set_value(450000.0)
    next(b for b in app.button if b.label == "Save & create my budgets").click().run()

    assert any("Please lower them by ₹300,000" in e.value for e in app.error)
    assert get_profile() is None  # nothing saved


def test_profile_edit_refuses_income_too_small_for_the_budgets():
    from tools.database_tool import get_profile, remove_all_data, save_profile, upsert_budget

    save_profile(20000, 2000, {})
    remove_all_data()
    upsert_budget("Food", 15000)

    app = AppTest.from_file(str(PAGES / "profile.py"), default_timeout=60).run()
    app.number_input(key="profile_income").set_value(10000.0)
    next(b for b in app.button if b.label == "Save").click().run()

    assert any("You can only budget ₹8,000" in e.value for e in app.error)
    assert get_profile()["monthly_income"] == 20000.0  # unchanged


def _budget_input(app, category):
    return next(n for n in app.number_input if n.label == f"{category} Budget (₹)")
