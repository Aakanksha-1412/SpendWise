# SPENDWISE — Autonomous Personal Financial Expense & Budgeting Assistant

An Agentic AI personal financial expense and budgeting assistant built with **Python 3.10+**, **Streamlit**, **LangChain / LangGraph**, **SQLite3**, **Pandas**, **Tesseract OCR / Vision LLM**, **ChromaDB**, and **Plotly**.

---

## 1. Project Overview & Agentic Concept

Unlike basic CRUD expense trackers with a bolted-on chatbot, **SpendWise** is designed around an **Agentic AI Orchestrator** (`agent/graph.py`). When a user submits a natural-language request, CSV statement, or receipt image, the central LangGraph controller:

1. **Understands the request**: Gemini reads the message (plus the recent chat for follow-ups).
2. **Decides which tool(s) to call**: Gemini chooses from 11 tools (`agent/tools_registry.py`) by function calling.
3. **Calls the tools**: LangGraph's `ToolNode` runs plain Python (OCR, categorization, SQLite, Pandas budget & spike detection).
4. **Evaluates the results**: the results go back to Gemini, which calls more tools if needed (a loop).
5. **Generates the final response / alert / suggestion**: every number comes from a tool, never from the LLM.

```text
START → [agent] Gemini decides ── tool requested? ── yes → [tools] Python runs it ──┐
           ▲                                       └─ no  → END (final answer)     │
           └──────────────────────── tool results go back to Gemini ◄──────────────┘
```

If Gemini is unavailable (no key, no internet, free-tier limit), the app falls back to a clearly
labelled keyword-based **Demo mode** (`agent/fallback_agent.py`) so it never breaks.

```text
Input Ingestion (Text / Image / CSV)
        ↓
LLM Central Controller (agent/graph.py)
        ↓
Tool Routing & Planning
        ↓
OCR / SQLite / Pandas (tools/* & analytics/*)
        ↓
State & Memory (SQLite + ChromaDB)
        ↓
Streamlit Dashboard + AI Insights (pages/*)
```

---

## 2. Folder Structure

```text
SpendWise/
│
├── app.py                        # Main Streamlit multi-page entry point & layout config
│
├── pages/                        # Member 4: UI Layer (Streamlit Pages — Zero raw SQL or Pandas math)
│   ├── home.py                   # Executive dashboard, summary KPIs, navigation cards, AI insights
│   ├── transactions.py           # Filterable ledger + Natural Language & Form expense entry
│   ├── upload.py                 # CSV bulk importer + Receipt OCR extraction pipeline UI
│   ├── budget.py                 # Monthly category budget configuration & status cards
│   ├── analytics.py              # 6 Plotly financial charts + Automated Spike Detection banner
│   ├── assistant.py              # Ask SpendWise AI chat interface with LangGraph trace viewer
│   ├── profile.py                # My Profile & Money Plan: income, savings goal, usual spending, charts
│   └── login.py                  # Log in / create account (shown until someone logs in)
│
├── agent/                        # Member 1: LangGraph Agentic Orchestrator
│   ├── graph.py                  # Gemini + LangGraph loop (agent ⇄ tools), run_agent() entry point
│   ├── tools_registry.py         # The 11 tools Gemini can request (wrap teammates' functions)
│   ├── memory.py                 # Short-term chat memory (per browser session)
│   ├── fallback_agent.py         # Keyword-based Demo mode when Gemini is unavailable
│   ├── state.py                  # AgentState schema (messages + fallback fields)
│   ├── prompts.py                # Gemini's rules (never invent numbers, memory rules ...)
│   ├── period.py                 # "Which month is it?" for the agent
│   └── tests/                    # Agent tests (fake Gemini, temporary database)
│
├── tools/                        # Deterministic Agent & UI Tools
│   ├── auth_tool.py              # Member 2: accounts; passwords stored only as salted PBKDF2 hashes
│   ├── ocr_tool.py               # Member 4: Receipt image -> Merchant, Date, Items, Tax, Total (Gemini Vision / Tesseract)
│   ├── database_tool.py          # Member 2: SQLite CRUD & query interfaces
│   ├── categorization_tool.py    # Member 2: Keywords + ChromaDB semantic categorization & NL expense parser
│   ├── budget_tool.py            # Member 3: Budget vs actual & discretionary reallocation
│   └── spike_detector.py         # Member 3: Weekly spending anomaly / spike detection
│
├── database/                     # Member 2: SQLite Setup & Schema
│   └── database.py               # Initializes `transactions` & `budgets` tables + demo seed data
│
├── analytics/                    # Member 3: Pandas Aggregation Layer
│   └── analytics.py              # DataFrames for category, weekly, monthly, and trend charts
│
├── utils/                        # Shared Helpers & Constants
│   └── helpers.py                # Official 8 categories, INR currency formatter, date normalizer
│
├── data/
│   └── sample_transactions.csv   # Sample transaction dataset for testing CSV ingestion
│
├── tests/                        # Member 5: tests for database, categorization, budget, spikes, OCR, pages
├── assets/                       # Static logos or sample receipt test images
├── .env.example                  # Environment variable template (Never commit real keys)
├── .gitignore                    # Git ignore rules for Python, SQLite, and .env
├── requirements.txt              # Python package dependencies (needed to run the app)
├── requirements-dev.txt          # + pytest & freezegun (needed only to run the tests)
└── README.md                     # Documentation & Team Collaboration Guide
```

---

## 3. Team Collaboration Guide (Who Works Where)

To prevent merge conflicts, each team member owns dedicated modules and communicates strictly through documented Python function interfaces:

| Role / Team Member | Owned Directories & Files | Public Function Contracts Exposed |
| :--- | :--- | :--- |
| **Member 1**<br>*(AI Agent / LangGraph)* | `agent/graph.py`<br>`agent/state.py`<br>`agent/prompts.py` | `run_agent(user_query, uploaded_receipt=None) -> dict` |
| **Member 2**<br>*(Database + Categorization)* | `database/database.py`<br>`tools/database_tool.py`<br>`tools/categorization_tool.py` | `add_transaction(tx)`<br>`get_transactions(category, merchant_query, date_filter)`<br>`get_category_spending(category, month, year)`<br>`categorize_expense(merchant, description) -> str` |
| **Member 3**<br>*(Analytics + Budget + Alerts)* | `analytics/analytics.py`<br>`tools/budget_tool.py`<br>`tools/spike_detector.py` | `calculate_budget_status(category)`<br>`suggest_discretionary_reallocation()`<br>`detect_spending_spike(category)` |
| **Member 4**<br>*(Streamlit UI + OCR)* | `app.py`<br>`pages/*.py`<br>`tools/ocr_tool.py` | `extract_receipt(image_file) -> dict`<br>Pages call the functions above; never write raw SQL or inline Pandas math. |
| **Member 5**<br>*(Testing + Integration)* | Testing checklist / test scripts | Tests each module and end-to-end flows (Receipt → OCR → Categorization → SQLite → Budget → Alert → AI response). |

---

## 4. Setup & Installation Instructions

### Step 1: Clone the Repository & Create a Virtual Environment
```bash
git clone <your-team-repo-url>
cd SpendWise

# Create and activate virtual environment (Linux / macOS)
python3 -m venv .venv
source .venv/bin/activate

# Or on Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
```bash
cp .env.example .env
```
Edit `.env` (never commit it):

| Variable | What it does |
| :--- | :--- |
| `GEMINI_API_KEY` | Your free key from aistudio.google.com. Without it the assistant runs in Demo mode. |
| `GEMINI_MODEL` | Gemini model for the agent and receipt OCR. Free tier ≈ 20 requests/day **per model**; use `gemini-3.5-flash-lite` while testing. If you get a 404 "model not found", pick a newer model. |
| `SPENDWISE_SEED_DEMO` | `true` (default) fills a new database with demo data dated relative to today. `false` starts empty for real use (delete `data/spendwise.db` to start over). |
| `CHROMA_PERSIST_DIR` | Where ChromaDB stores learned merchants (default `data/chroma_memory`). First use downloads an ~80 MB model once. |
| `TESSERACT_CMD_PATH` | Optional: path to `tesseract.exe` if Tesseract OCR is installed. |
| `SPENDWISE_DB_PATH` | Optional: custom SQLite file location. |

### Step 4: Run the Streamlit Application
```bash
streamlit run app.py
```

### Step 5: Run the Tests
```bash
pip install -r requirements-dev.txt
python -m pytest agent/tests tests -v
```

---

## 5. Where Each Technology Is Used

| Technology | Where | What it does |
| :--- | :--- | :--- |
| **LLM API (Gemini)** | `agent/graph.py`, `tools/ocr_tool.py` | Plans and picks tools; reads receipt photos (Vision) |
| **LangChain / LangGraph** | `agent/` | Tool definitions (`@tool`), the agent ⇄ tools loop, state |
| **SQLite3** | `database/`, `tools/database_tool.py` | Transactions & budgets (budgets carry over to new months) |
| **Pandas** | `analytics/`, `tools/budget_tool.py`, `tools/spike_detector.py` | Budget vs actual, weekly spikes (last 7 days vs previous 7), trends |
| **Tesseract OCR / Vision LLM** | `tools/ocr_tool.py` | Gemini Vision → Tesseract (if installed) → labelled demo receipt |
| **ChromaDB** | `tools/categorization_tool.py` | Semantic merchant memory: "Chai Point" → Food; learns from saved expenses |
| **Plotly** | `pages/home.py`, `pages/analytics.py` | Interactive charts |
| **Memory** | `agent/memory.py` + SQLite + ChromaDB | Chat follow-ups ("yes, log it"), stored data, learned merchants |

### Accounts (login)
The app opens on a **Log in / Create account** screen. Each account only sees its own expenses,
budgets, profile and learned shops. Passwords are never stored, only salted PBKDF2-SHA256 hashes.
A new account can start with demo data, or take over data saved on this computer before login
existed (older databases are upgraded automatically, keeping their data).

### Asking the assistant about money
- "How much can I still save this month?" / "Am I on track?" (uses your profile)
- "Set my food budget to 5000" / "My income is now 25000" / "I want to save 4000" (changes them)
- When you add an expense in chat and it eats into your savings goal, SpendWise warns you.

### Using your own data
A new account opens on **"Welcome! Let's set up your budget"**: enter your monthly income, savings goal
and your budget per category (or leave the budgets empty and SpendWise splits your money automatically),
then click **Save & create my budgets**. Each number lives in ONE place afterwards:
**👤 My Profile** = income & savings goal only; **🎯 Budget Manager** = budgets per category (it warns if
they add up to more than income − savings goal).

### Known limits
- Free Gemini tier: about 5 requests/minute and 20/day per model (one question = 2–3 requests).
- Merchants with meaningless names (e.g. "XYZ Traders") stay "Others" until saved once with a category.
