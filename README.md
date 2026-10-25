# SPENDWISE

**Autonomous Personal Financial Expense & Budgeting Assistant**

The entire project lives in the [`SpendWise/`](SpendWise/) folder (Python + Streamlit + LangGraph + Gemini).
See [`SpendWise/README.md`](SpendWise/README.md) for the full guide: features, technology, architecture,
every page and chart, the money rules, the AI assistant, setup, tests and team ownership.

## Quick start

```bash
cd SpendWise
python -m venv .venv
.venv\Scripts\activate        # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py          # opens http://localhost:8501
```

## Team workflow

1. `git pull origin main` before you start work.
2. Work on your own branch: `git checkout -b feature/<your-module>`.
3. Only edit the files your role owns (see the ownership table in `SpendWise/README.md`).
4. Push your branch and open a Pull Request. Never push directly to `main`.
