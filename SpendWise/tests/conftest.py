"""
Shared test setup for the team modules (database, categorization, budget, spikes, OCR, pages).

Run from the SpendWise folder:
    pip install -r requirements-dev.txt
    python -m pytest tests -v
"""

import pytest

import database.database as database


@pytest.fixture(scope="session", autouse=True)
def test_chroma_dir(tmp_path_factory):
    """ChromaDB learns into a temporary folder, never into data/chroma_memory."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("CHROMA_PERSIST_DIR", str(tmp_path_factory.mktemp("chroma")))
        yield


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Temporary database; no Gemini key (so OCR / agent never call Google in tests)."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("SPENDWISE_SEED_DEMO", "true")
