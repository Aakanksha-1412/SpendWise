"""
Shared test setup for the agent (Member 1).

Run from the SpendWise folder:
    pip install -r requirements-dev.txt
    python -m pytest agent/tests -v

- `fresh_db`   : every test gets its own temporary SQLite database with the demo data
                 (your real data/spendwise.db is never touched).
- `fake_gemini`: replaces Gemini with a script of replies, so tests are free, fast and
                 can simulate failures (rate limits) on purpose.
"""

import pytest
from langchain_core.messages import AIMessage

import agent.graph as graph
import utils.helpers as helpers
import database.database as database
from agent import memory


@pytest.fixture(scope="session", autouse=True)
def test_chroma_dir(tmp_path_factory):
    """Keep ChromaDB's learned merchants in a temporary folder, never in data/chroma_memory."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CHROMA_PERSIST_DIR", str(tmp_path_factory.mktemp("chroma")))
        yield


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "spendwise_test.db"))
    database.init_db()


@pytest.fixture(autouse=True)
def new_chat():
    """Every test starts with an empty chat memory."""
    memory.forget_all()
    yield
    memory.forget_all()


class FakeGemini:
    """Plays back scripted replies in order. An Exception in the script is raised instead."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0
        self.received = []  # the message lists we sent to "Gemini", one per call

    def invoke(self, messages):
        self.calls += 1
        self.received.append(list(messages))
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


@pytest.fixture
def fake_gemini(monkeypatch):
    """Usage: fake = fake_gemini([gemini_asks(...), gemini_says("...")])"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def install(script):
        fake = FakeGemini(script)
        monkeypatch.setattr(graph, "_build_llm", lambda api_key, model: fake)
        return fake

    return install


@pytest.fixture
def no_gemini(monkeypatch, tmp_path):
    """No API key anywhere (also hides your real SpendWise/.env), so demo mode is used."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(helpers, "ENV_FILE_PATH", str(tmp_path / "missing.env"))


def gemini_asks(*calls):
    """A Gemini reply that requests tools: gemini_asks(("add_expense", {...}), ...)."""
    return AIMessage(
        "",
        tool_calls=[{"name": name, "args": args, "id": f"call_{i}", "type": "tool_call"} for i, (name, args) in enumerate(calls)],
    )


def gemini_says(text):
    """A Gemini reply with the final answer text."""
    return AIMessage(text)
