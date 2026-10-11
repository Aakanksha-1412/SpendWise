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


def test_profile_page_saves_income_creates_budgets_and_removes_demo_data():
    from tools.database_tool import get_all_budgets, get_profile, get_transactions

    app = AppTest.from_file(str(PAGES / "profile.py"), default_timeout=60).run()
    assert get_transactions()  # demo data before setup

    app.number_input(key="profile_income").set_value(20000.0)
    app.number_input(key="profile_savings").set_value(3000.0)
    app.number_input(key="profile_usual_Food").set_value(4000.0)
    app.number_input(key="profile_usual_Bills").set_value(2500.0)
    app.button[0].click().run()  # "Save & create my budgets" (start fresh is ticked by default)

    assert not app.exception
    assert get_profile()["monthly_income"] == 20000.0
    assert get_transactions() == []
    assert get_all_budgets()["Food"] == 4000.0
    assert any("Saved!" in message.value for message in app.success)


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
