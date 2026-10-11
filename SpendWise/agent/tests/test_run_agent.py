"""
Seam: run_agent(question) — the same function the Ask SpendWise page calls.
Gemini is replaced by a scripted fake (see conftest.py).
"""

import database.database as database
from agent.graph import run_agent
from agent.tests.conftest import gemini_asks, gemini_says


def test_a_crashing_tool_is_reported_to_gemini_instead_of_crashing_the_page(fake_gemini, tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path))  # a folder, not a file: SQLite can't open it
    fake_gemini([
        gemini_asks(("get_budget_status", {"category": "Food"})),
        gemini_says("Sorry, I couldn't read your budget right now."),
    ])

    result = run_agent("how much food budget is left?")

    assert result["response"] == "Sorry, I couldn't read your budget right now."
    assert "error" in str(result["tool_outputs"]["get_budget_status"]).lower()


def test_rejected_save_followed_by_gemini_outage_does_not_claim_it_was_saved(fake_gemini):
    fake_gemini([
        gemini_asks(("add_expense", {"merchant": "DMart", "amount": 300, "category": "Groceries"})),
        ConnectionError("network down"),
    ])

    result = run_agent("add 300 at dmart")

    assert "was saved" not in result["response"]


def test_waits_and_retries_once_when_gemini_free_limit_is_hit(fake_gemini, monkeypatch):
    from langchain_google_genai.chat_models import GoogleRateLimitError
    import agent.graph as graph

    monkeypatch.setattr(graph, "RATE_LIMIT_WAIT_SECONDS", 0)  # don't really wait in tests
    fake = fake_gemini([
        GoogleRateLimitError("429 RESOURCE_EXHAUSTED"),
        gemini_says("Your food budget has ₹2,000 left."),
    ])

    result = run_agent("how much food budget is left?")

    assert result["mode"] == "llm"
    assert result["response"] == "Your food budget has ₹2,000 left."
    assert fake.calls == 2


def test_does_not_wait_when_the_daily_limit_is_used_up(fake_gemini, monkeypatch):
    from langchain_google_genai.chat_models import GoogleRateLimitError
    import agent.graph as graph

    waits = []
    monkeypatch.setattr(graph.time, "sleep", waits.append)
    fake = fake_gemini([
        GoogleRateLimitError("429 RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier"),
        gemini_says("never reached"),
    ])

    result = run_agent("how much food budget is left?")

    assert waits == []
    assert fake.calls == 1
    assert result["mode"] == "fallback"


def test_demo_mode_reports_the_current_month_not_october(no_gemini):
    from freezegun import freeze_time
    from agent.tools_registry import add_expense

    with freeze_time("2026-11-05"):
        add_expense.invoke({"merchant": "Canteen", "amount": 400, "category": "Food", "date": "03-11-2026"})

        result = run_agent("how much did I spend on food?")

    assert result["mode"] == "fallback"
    assert "November 2026" in result["response"]
    assert "**Actual Spent:** **₹400**" in result["response"]  # not October's demo ₹3,000


def test_demo_mode_says_when_a_receipt_photo_could_not_be_read(no_gemini, monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD_PATH", "")
    monkeypatch.setattr("shutil.which", lambda name: None)

    result = run_agent("add this receipt and tell me my food budget", uploaded_receipt=b"not-an-image")

    assert result["mode"] == "fallback"
    assert "couldn't read" in result["response"]
