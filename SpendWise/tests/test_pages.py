"""Member 4: every page opens; the assistant keeps question + answer together.
(conftest.py sets GEMINI_API_KEY="" so the assistant runs in demo mode with no Google calls.)"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

# Load the real `analytics` package first: when AppTest runs pages/analytics.py it puts the
# pages/ folder on the import path, and "analytics" could otherwise resolve to that page file.
import analytics.analytics  # noqa: F401

PAGES = Path(__file__).resolve().parents[1] / "pages"


@pytest.mark.parametrize("page", ["home", "transactions", "upload", "budget", "analytics", "assistant"])
def test_page_opens_without_errors(page):
    app = AppTest.from_file(str(PAGES / f"{page}.py"), default_timeout=60).run()

    assert not app.exception


def test_assistant_shows_question_and_answer():
    app = AppTest.from_file(str(PAGES / "assistant.py"), default_timeout=60).run()
    app.chat_input[0].set_value("how much food budget is left?").run()

    history = app.session_state["chat_history"]
    assert history[-2]["role"] == "user" and history[-2]["content"] == "how much food budget is left?"
    assert history[-1]["role"] == "assistant" and "Food" in history[-1]["content"]
