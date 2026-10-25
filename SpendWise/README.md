# SPENDWISE — Autonomous Personal Financial Expense & Budgeting Assistant

SpendWise is a personal money app for students in India. You tell it your **monthly income** and how much you
want to **save**, set a **budget for each spending category**, and add your expenses: typed in a sentence,
filled in a form, uploaded as a **receipt photo**, or imported from a **bank statement (CSV)**.
SpendWise then shows where your money goes, warns you when a budget is over or spending suddenly jumps,
and has an **AI assistant** you can ask questions like *"Can I afford ₹2,000 on shopping?"*.

Built with **Python 3.12**, **Streamlit**, **LangChain / LangGraph + Google Gemini**, **SQLite**, **Pandas**,
**Plotly**, **ChromaDB** and **Tesseract OCR / Gemini Vision**.

---

## Contents

1. [What you can do with SpendWise](#1-what-you-can-do-with-spendwise)
2. [Technology used and where](#2-technology-used-and-where)
3. [How it works (architecture)](#3-how-it-works-architecture)
4. [Folder structure](#4-folder-structure)
5. [Every page explained](#5-every-page-explained)
6. [The money rules (all the maths)](#6-the-money-rules-all-the-maths)
7. [Every chart explained](#7-every-chart-explained)
8. [How expenses are checked before saving](#8-how-expenses-are-checked-before-saving)
9. [The AI assistant](#9-the-ai-assistant)
10. [Where the data is stored](#10-where-the-data-is-stored)
11. [Accounts, login and privacy](#11-accounts-login-and-privacy)
12. [Setup and running the app](#12-setup-and-running-the-app)
13. [Tests](#13-tests)
14. [Deploying online](#14-deploying-online)
15. [Team ownership](#15-team-ownership)
16. [Known limits](#16-known-limits)

---

## 1. What you can do with SpendWise

| Feature | What it means for you |
| :--- | :--- |
| **Money plan** | Enter income and a savings goal once. SpendWise shows how much you can still spend this month *and still keep your savings goal*. |
| **Budgets per category** | 8 categories: Food, Transport, Shopping, Entertainment, Bills, Healthcare, Education, Others. All budgets together can never be more than *income − savings goal*. |
| **4 ways to add expenses** | Type a sentence ("Spent ₹450 at Swiggy"), fill a form, upload a receipt photo, or import a bank/UPI statement CSV. |
| **Automatic categories** | "Swiggy" → Food, "Uber" → Transport, "Apollo Pharmacy" → Healthcare. Unknown shops are guessed by meaning (ChromaDB) and learned for next time. |
| **Alerts** | Over-budget alerts ("Shopping is over by ₹1,500") and weekly spending spike alerts ("Food +160% vs last week"). |
| **Charts** | 5 Analytics charts, a Home dashboard and a money-plan donut. All amounts are written the Indian way (₹2,00,000). |
| **AI assistant** | Ask questions in plain English. Gemini picks the right tools; every number comes from your real data, never made up. Works in a simpler **demo mode** without Gemini. |
| **Edit / delete** | Correct or remove any expense on the Transactions page. |
| **Accounts** | Each person logs in and sees only their own data. You stay logged in after a page refresh (7 days). |

---

## 2. Technology used and where

| Technology (version) | Where in the code | What it is used for |
| :--- | :--- | :--- |
| **Python 3.12** (3.11 minimum) | everywhere | The language of the whole project. |
| **Streamlit 1.65** | `app.py`, `pages/` | The web app: pages, forms, buttons, login screen. |
| **Google Gemini** (LLM API) | `agent/graph.py`, `tools/ocr_tool.py` | Understands questions and chooses tools; reads receipt photos (Gemini Vision). |
| **LangChain 1.4 / LangGraph 1.2** | `agent/` | Turns Python functions into tools (`@tool`) and runs the *agent ⇄ tools* loop. |
| **SQLite** (Python built-in) | `database/database.py`, `tools/database_tool.py`, `tools/auth_tool.py` | Stores accounts, expenses, budgets, profiles and login keys in one file `data/spendwise.db`. |
| **Pandas 3.0** | `analytics/`, `tools/database_tool.py`, `tools/spike_detector.py` | Totals per category / month / week / day for the charts and alerts. |
| **Plotly 7.1** | `pages/home.py`, `pages/analytics.py`, `pages/profile.py` | Interactive charts (bars, pie, donut, line). |
| **ChromaDB 1.5** | `tools/categorization_tool.py` | "Meaning-based" memory: guesses a category for shops it has never seen and remembers shops you saved. |
| **Tesseract OCR + Pillow** | `tools/ocr_tool.py` | Reads text from receipt photos when Gemini isn't available. |
| **python-dotenv** | `utils/helpers.py` | Reads settings from the `.env` file. |
| **pytest + freezegun** | `tests/`, `agent/tests/` | Automated tests (freezegun fixes "today's date" inside a test). |

---

## 3. How it works (architecture)

### The layers

```text
 You (browser)
     │
     ▼
 Streamlit pages ─────────────── pages/*.py      (only screens: no SQL, no money maths)
     │
     ├─► AI assistant ────────── agent/*.py       (Gemini + LangGraph, or demo mode)
     │        │
     ▼        ▼
 Tools & analytics ──────────── tools/*.py, analytics/analytics.py   (all rules and maths live here)
     │
     ▼
 Storage ─────────────────────── SQLite (data/spendwise.db) + ChromaDB (data/chroma_memory/)
```

**Rule of the project:** pages never write SQL or do money maths. They call functions in `tools/` and
`analytics/`, so the same numbers appear everywhere (Home, Profile, Budget, Analytics and the assistant).

### How the AI assistant answers a question

```text
START → [agent] Gemini reads the question ── wants a tool? ── yes → [tools] Python runs it ──┐
           ▲                                                └─ no  → END (final answer)      │
           └────────────────────────── tool result goes back to Gemini ◄────────────────────┘
```

1. **Understand** – Gemini reads your message (plus the last 6 chat messages, for follow-ups like "yes, log it").
2. **Decide** – Gemini chooses from **14 tools** (`agent/tools_registry.py`).
3. **Call** – LangGraph's `ToolNode` runs the plain Python function (SQLite, Pandas, OCR...).
4. **Evaluate** – the result goes back to Gemini, which may call more tools (at most 12 steps).
5. **Answer** – Gemini replies using only numbers that came from the tools.

If Gemini can't be used (no API key, no internet, free daily limit reached), the app switches to a clearly
labelled **demo mode** (`agent/fallback_agent.py`): fixed keyword rules + the same tools, no AI.

### Where a new expense goes

```text
Sentence / form / receipt photo / CSV
   → read & clean (amount, date, shop)          tools/categorization_tool.py, ocr_tool.py, csv_import_tool.py
   → checked (real date, not future, amount > 0, not money received, not a duplicate)
   → category chosen (keywords → ChromaDB)     tools/categorization_tool.py
   → saved in SQLite                            tools/database_tool.py
   → budgets, alerts and charts update          tools/budget_tool.py, spike_detector.py, analytics/analytics.py
```

---

## 4. Folder structure

```text
SpendWise/
├── app.py                     # Entry point: page setup, styling, login gate, "stay logged in", sidebar
│
├── pages/                     # The screens (Streamlit). No SQL or money maths here.
│   ├── login.py               # Log in / create account
│   ├── home.py                # Dashboard: income line, 4 cards, budget vs actual chart, alerts, category cards
│   ├── transactions.py        # Add expenses (sentence or form), month filter, list, edit / delete
│   ├── upload.py              # CSV statement import + receipt photo reading
│   ├── budget.py              # Set budgets (max = income − savings), status cards, ledger table
│   ├── analytics.py           # Spike alerts + 5 charts
│   ├── assistant.py           # "Ask SpendWise" chat with a step-by-step trace
│   └── profile.py             # First-time setup, money plan (donut + budget vs spent), edit income/savings
│
├── agent/                     # The AI assistant
│   ├── graph.py               # Gemini + LangGraph loop; run_agent() used by the chat page
│   ├── tools_registry.py      # The 14 tools Gemini may call
│   ├── prompts.py             # Gemini's rules (never invent numbers, only save when asked, ...)
│   ├── memory.py              # Short chat memory per browser session
│   ├── state.py               # The data passed between graph steps
│   ├── fallback_agent.py      # Demo mode (keyword rules) when Gemini is unavailable
│   └── tests/                 # Assistant tests (Gemini is replaced by a scripted fake)
│
├── tools/                     # All business rules
│   ├── auth_tool.py           # Accounts, password hashing, login keys
│   ├── database_tool.py       # Add / read / edit / delete expenses, budgets, profile
│   ├── budget_tool.py         # Budget status, "budgets must fit the income" rule, saving suggestions
│   ├── categorization_tool.py # Keyword + ChromaDB categories; reads typed sentences
│   ├── spike_detector.py      # This week vs last week
│   ├── ocr_tool.py            # Receipt photo → shop, date, items, tax, total
│   └── csv_import_tool.py     # Bank / UPI CSV → clean expenses
│
├── analytics/analytics.py     # Numbers for the cards and charts (money plan, summaries, trends)
├── database/database.py       # Creates / upgrades the SQLite tables, demo data
├── utils/helpers.py           # Categories, ₹ formatting (Indian style), date reading and checks, settings
├── data/
│   ├── sample_transactions.csv     # Clean CSV example (with categories)
│   └── sample_messy_statement.csv  # Messy CSV example (no categories, "1,500" amounts)
├── tests/                     # Tests for database, pages, profile, CSV, OCR, categories, spikes, login
├── assets/                    # Images (empty for now)
├── .env.example               # Settings template — copy to .env
├── requirements.txt           # Libraries needed to run the app
└── requirements-dev.txt       # + pytest and freezegun for the tests
```

---

## 5. Every page explained

### 🔐 Log in / Create account
- Log in with username + password, or create an account (username 3–30 letters/numbers/`_`/`.`, password at least 6 characters).
- "Start with demo data" gives a new account sample expenses, budgets and alerts — handy for a presentation.

### 👤 My Profile & Setup
- **First time:** enter monthly income, savings goal, and a budget per category. Leave the budgets empty and
  SpendWise splits *income − savings goal* across the categories for you. Budgets that add up to more than you
  can plan are refused.
- **Afterwards:** shows your **money plan** for the month:
  - 4 numbers: Monthly income · Savings goal · Spent so far · You can still spend.
  - **"How your income is split"** donut and **"Budget vs spent"** bars (see [section 7](#7-every-chart-explained)).
  - **Budget status** per category: ✅ fine · ⚠️ almost full · ⚠️ full · 🚨 over by ₹X · – no budget.
  - "Edit income & savings goal" — refused if your current budgets would no longer fit.

### 🏠 Home Dashboard
- Income line: *Income · Left after spending · Savings goal ✅ on track / ⚠️ not on track*.
- 4 cards: **Total Spent** (this month) · **Monthly Budget** (red note if more than you can plan) ·
  **Remaining Budget** ("Left to spend this month") · **Budget Alerts** (over-budget + spikes).
- "Budget vs Actual Spending by Category" chart, AI insights & saving suggestions, a card per category.

### 🧾 Transactions
- **Add an expense** by sentence ("Spent ₹450 at Swiggy for dinner on 01-10-2026") or by form.
- **Filter** by month (default: this month, so the total matches Home), category, shop name or exact date.
- The list is sorted newest date first, with a total for the chosen period.
- **Edit or delete an expense**: pick one, change any field, or delete it (needs a confirmation tick).

### 📤 Upload Expense
- **CSV statement:** columns `date, merchant, amount` (+ optional `description`, `category`, `type`/`Dr/Cr`).
  You see a preview and the reason for every skipped row before importing.
- **Receipt photo (JPG/PNG):** read by Gemini Vision, else Tesseract; you check/correct the shop, date, total,
  tax and category before saving. "Run Demo Receipt Extraction" tries it without a photo.

### 🎯 Budget Manager
- Change budgets for all 8 categories. The form says the maximum (*income − savings goal*) and refuses more.
- Status cards with a progress bar per category, and a full ledger table.

### 📊 Spending Analytics
- Spike alerts at the top, then 5 charts (see [section 7](#7-every-chart-explained)).

### 🤖 Ask SpendWise AI
- Chat with the assistant, with example questions. Each answer shows a trace of which tools were used.
- A receipt photo can be attached to a message ("add this receipt").

---

## 6. The money rules (all the maths)

All amounts are for the **current calendar month**, shown in Indian format (`₹2,00,000`, `₹12,50,000`).

| Number | Formula | Example (income ₹2,00,000 · savings ₹50,000 · spent ₹24,380) |
| :--- | :--- | :--- |
| **Money you can plan** | income − savings goal | ₹2,00,000 − ₹50,000 = **₹1,50,000** |
| **Budget limit** | all budgets together ≤ money you can plan | budgets of ₹1,10,000 ✅; ₹5,47,500 ❌ refused |
| **You can still spend** | income − savings goal − spent | ₹1,50,000 − ₹24,380 = **₹1,25,620** |
| **Left after spending** | income − spent | ₹1,75,620 (on track while ≥ savings goal) |
| **Remaining Budget** (Home) | the smaller of *(budgets − spent)* and *(you can still spend)* | min(₹85,620, ₹1,25,620) = **₹85,620** |
| **Category remaining** | category budget − category spent | Shopping ₹8,000 − ₹9,500 = **−₹1,500** |

**Category status:** no budget → *no budget* · spent > budget → *🚨 over by ₹X* · spent = budget → *⚠️ full* ·
spent ≥ 80% → *⚠️ almost full* · otherwise *✅ fine*.

**"Can I afford ₹X?"** — **Yes** only if the category budget has ₹X left **and** ₹X fits in *you can still spend*.
Otherwise the assistant explains, e.g. *"No. You only have ₹1,38,600 left to spend this month while keeping
your ₹50,000 savings goal. Spending ₹1,50,000 would cut into your savings by ₹11,400."*

**Spending spike** — compares the **last 7 days** (including today) with the **7 days before**:
- increase % = (this week − last week) ÷ last week × 100. It can be above 100%: **+100% = double**,
  +275% = 3.75 times (₹2,000 → ₹7,500).
- A spike needs **+35% or more AND at least ₹300 more**.
- If last week was ₹0 there is no percentage (shown as "new"): ₹300+ is a spike only if that category had
  spending before; a category's very first spending is never called a spike.

**Budgets carry over:** a new month starts with last month's budgets until you change them.

---

## 7. Every chart explained

### Profile — "How your income is split" (donut)
The whole circle is **your income**. Its parts always add up to exactly the income:
1. **Spent so far** (red)
2. **Savings goal** (green) — e.g. ₹50,000 of ₹2,00,000 = **25%**
3. **Budget left** (teal) — unspent budget, but never more than the money really left
4. **Not planned yet** (grey) — income not given to any budget

Example: ₹24,380 + ₹87,120 + ₹50,000 + ₹38,500 = **₹2,00,000**.

### Profile / Home / Analytics — "Budget vs spent" (grouped bars)
Two bars per category: the light bar is the **budget**, the coloured bar is what you **spent** this month
(red when over budget on Home and Profile).

### Analytics 1 — Category-Wise Spending Distribution (pie)
Your spending **this month** split by category. The percentages are *shares* of the total, so they add up to 100%.

### Analytics 2 — Budget vs Actual Spending (grouped bars)
Same idea as above, for all 8 categories.

### Analytics 3 — Weekly Spending Comparison (grouped bars)
For each category: grey = **previous 7 days**, blue = **last 7 days**. This is what the spike alerts are based on.

### Analytics 4 — Monthly Spending Overview (bars)
One bar per month = everything spent in that month, so you can compare months (e.g. Sep ₹7,200 · Oct ₹24,380).

### Analytics 5 — Daily & Cumulative Spending Trend (bars + line)
Two things on the same ₹ scale, for the current month:
- **Grey bars = daily spend** — how much you spent on that one day.
- **Green line = running total** — everything spent this month up to that day (each point = previous point + that day's bar).

The bars show *which days were expensive*; the line shows *how fast the month's total grows*. The line's last
point equals "Total Spent" on Home.

---

## 8. How expenses are checked before saving

Every way of adding an expense uses the same rules, and explains in plain English when something isn't saved.

| Check | Example refused | Message |
| :--- | :--- | :--- |
| Real calendar date | 31-02-2026, 10-13-2026 | *"31-02-2026" is not a real date. Please write the date as DD-MM-YYYY…* |
| Not in the future | 10-11-2026 (when today is 25-10-2026) | *The date 10-11-2026 is in the future. Please use today's date or an earlier one.* |
| Not money received | "Got refund of 500 from Amazon", salary, CR rows | *This looks like money you received, not money you spent…* |
| Amount found | "Swiggy dinner on 01-10-2026" (no amount) | *I couldn't find an amount. Please include it, for example ₹450.* |
| Receipt has shop and total | empty shop name, ₹0 total | *Please enter the shop name.* / *…the bill total (more than ₹0).* |
| Not a duplicate receipt | same date + shop + total already saved | *You already saved ₹550 at Starbucks Coffee on 25-10-2026…* (tick box to save anyway) |

**Reading amounts and dates**
- Amounts: `₹1,25,000`, `125,000`, `Rs 300`, `450 rupees`, `300.00 Dr`. Percentages ("2.5%") are never money.
- Dates: `25-10-2026`, `2026-10-25`, `25/10/2026`, `25 Oct 2026`, `25-Oct-2026`, `25/10/26`, plus "today"/"yesterday" in sentences.

**Receipts (Tesseract text rules)** — the *Grand/Net Total* line is the bill total; "Total GST/Tax" lines count as tax;
cash handed over and change are ignored; headings like "Tax Invoice" are not the shop name.

**CSV import** — credits (CR / Credit type, "500 CR", negative or `(500)` amounts) are skipped; unreadable rows are
skipped with the row number and reason; rows already saved are not saved again, but two real identical purchases
in one file are both kept; the import is all-or-nothing.

**Categories** — keywords are matched as **whole words** ("vi" doesn't match "multivitamin"); the shop name decides
before the description; the longest keyword wins ("Metro Shoes" → Shopping, "Delhi Metro" → Transport). If no keyword
matches, ChromaDB compares the name by meaning; if unsure, the category is **Others**.

---

## 9. The AI assistant

### The 14 tools Gemini can use (`agent/tools_registry.py`)

| Reads data | Changes data |
| :--- | :--- |
| `get_budget_status` — one category's budget, spent, left | `add_expense` — save an expense (refuses future/impossible dates) |
| `get_all_budgets_overview` — all 8 categories | `set_budget` — change a budget (refused if over the limit) |
| `get_monthly_summary` — totals, income, savings | `update_my_profile` — change income / savings goal (refused if budgets wouldn't fit) |
| `get_saving_suggestions` — where to cut back | |
| `get_my_profile` — income, savings goal, saved so far | |
| `check_spending_spike` / `check_all_spending_spikes` | |
| `search_transactions` — find expenses (newest first) | |
| `check_affordability` — "can I afford ₹X on Y?" (budget **and** savings goal) | |
| `suggest_category` — category for a shop | |
| `read_uploaded_receipt` — read an attached receipt photo | |

### Safety rules (in `agent/prompts.py` and the code)
- Never invent numbers — every amount comes from a tool.
- Only save when you clearly ask; never save the same expense twice from chat history.
- If Gemini stops halfway after saving something, the reply says exactly what was saved.
- **Demo mode** saves only on a clear request ("add / spent / paid / bought" + an amount, or an attached photo);
  questions and "what if"s ("If I spent ₹500…") are never saved; a bare "yes, log it" asks for the full expense.

### Example questions
- "How much of my food budget is left?" · "Why did I receive a shopping alert?"
- "Can I afford ₹2,000 on shopping?" · "Which category increased the most?"
- "Add ₹450 at Swiggy for food and tell me my food budget left"
- "Set my food budget to 5000" · "My income is now 25000" · "I want to save 4000"

### Memory
- **Chat memory** (`agent/memory.py`): the last messages of the current chat, so follow-ups make sense.
- **Merchant memory** (ChromaDB): shops you saved with a category are recognised next time.

---

## 10. Where the data is stored

One SQLite file, `data/spendwise.db` (created automatically, never committed):

| Table | What it holds |
| :--- | :--- |
| `users` | username, password hash + salt |
| `login_sessions` | hashed "stay logged in" keys with an expiry date |
| `transactions` | date (DD-MM-YYYY), merchant, amount, category, description, source (Text/CSV/Receipt) |
| `budgets` | one budget per category per month |
| `profile` | monthly income and savings goal |
| `usual_spending` | usual spending per category (used to suggest budgets) |

Every row has a `user_id`, and every query only reads the logged-in user's rows. Older databases (from before
login existed) are upgraded automatically without losing data.
ChromaDB keeps learned shop names in `data/chroma_memory/`.

---

## 11. Accounts, login and privacy

- **Passwords are never stored** — only a salted PBKDF2-SHA256 hash (200,000 rounds).
- **Stay logged in:** after login a random key is kept in a browser cookie for 7 days (`SameSite=Strict`, `Secure`
  on https). Only its SHA-256 hash is in the database. Logging out deletes it immediately.
- Each user only sees and can only edit/delete **their own** expenses.
- Receipt photos are sent to Google Gemini when a key is set — don't upload private documents to the online demo.
- Never commit `.env`, `data/*.db` or personal bill photos to GitHub (`.gitignore` already excludes the first two).

---

## 12. Setup and running the app

> Requires **Python 3.12** (3.11 also works; 3.10 does **not**, because pandas 3 needs 3.11+). Check with `python --version`.

```bash
git clone https://github.com/Aakanksha-1412/SpendWise.git
cd SpendWise/SpendWise

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
cp .env.example .env              # then edit .env (see below)
streamlit run app.py              # opens http://localhost:8501
```

| Setting in `.env` | What it does |
| :--- | :--- |
| `GEMINI_API_KEY` | Free key from aistudio.google.com. Without it, the assistant runs in demo mode and receipts use Tesseract / the demo receipt. |
| `GEMINI_MODEL` | Gemini model for the assistant and receipt reading. If you get a 404 "model not found", use a newer model name. |
| `SPENDWISE_SEED_DEMO` | `true` (default): a brand-new database starts with demo data dated relative to today. `false`: start empty. |
| `SPENDWISE_DB_PATH` | Optional: a different SQLite file. |
| `CHROMA_PERSIST_DIR` | Where ChromaDB stores learned shops (default `data/chroma_memory`). First use downloads an ~80 MB model once. |
| `TESSERACT_CMD_PATH` | Optional: path to `tesseract.exe` if Tesseract OCR is installed but not on PATH. |
| `SPENDWISE_ONLINE_DEMO` | `true` shows an "online demo" notice on the login page. |

**First use:** create an account → fill in income, savings goal and budgets → start adding expenses.
For a presentation, tick **"Start with demo data"** when creating the account.

---

## 13. Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

**153 tests** cover: the money rules and the income donut, budget limits on every page and in the assistant,
Indian number format, date checks (future / impossible / bank formats), typed sentences, receipts and duplicates,
CSV import (credits, `nan`, all-or-nothing), categories, spike maths, Transactions filters/edit/delete,
login/logout and login keys, and the assistant (with a scripted fake Gemini and in demo mode).
Tests use a temporary database, so your real data is never touched.

---

## 14. Deploying online

Streamlit Community Cloud (free):
1. Sign in at **share.streamlit.io** with GitHub → **Create app** → *Deploy a public app from GitHub*.
2. Repository `Aakanksha-1412/SpendWise`, branch `main`, main file path `SpendWise/app.py`.
3. **Advanced settings** → Python version **3.12** → **Secrets**:
   ```toml
   GEMINI_API_KEY = "your-key"            # preferably a separate key just for the demo
   GEMINI_MODEL = "your-gemini-model"
   SPENDWISE_ONLINE_DEMO = "true"
   ```
4. **Deploy.** The app updates automatically after each merge into `main` (or use *Reboot app*).

On the free plan the server can restart, which resets the SQLite data and accounts — fine for a demo.
Everyone using the link shares the Gemini key's free daily limit.

---

## 15. Team ownership

Each member owns their files and talks to the others only through these functions, to avoid merge conflicts.
Work on a branch and open a Pull Request — never push directly to `main`.

| Member | Owns | Main functions others use |
| :--- | :--- | :--- |
| **Member 1** — AI agent | `agent/` | `run_agent(user_query, uploaded_receipt=None, chat_history=None) -> dict` |
| **Member 2** — Database, accounts, categories | `database/`, `tools/database_tool.py`, `tools/auth_tool.py`, `tools/categorization_tool.py` | `add_transaction`, `get_transactions`, `update_transaction`, `delete_transaction`, `get_all_budgets`, `upsert_budget`, `get_profile`, `categorize_expense`, `create_user`, `verify_user` |
| **Member 3** — Analytics, budgets, alerts | `analytics/`, `tools/budget_tool.py`, `tools/spike_detector.py` | `get_money_plan`, `get_summary_metrics`, `check_spend_against_savings`, `calculate_budget_status`, `check_budgets_fit`, `detect_spending_spike` |
| **Member 4** — UI, OCR, CSV | `app.py`, `pages/`, `tools/ocr_tool.py`, `tools/csv_import_tool.py` | `extract_receipt`, `read_transactions_csv`, `import_rows` |
| **Member 5** — Testing | `tests/`, `agent/tests/` | End-to-end checks: receipt → OCR → category → SQLite → budget → alert → AI answer |

---

## 16. Known limits

- **Gemini free tier:** about 5 requests per minute and 20 per day per model; one question uses 2–3 requests.
  When the limit is reached, the assistant switches to demo mode.
- **Monthly chart** compares months with each other only; past income isn't stored, so old months aren't compared with income.
- **Shops with meaningless names** (e.g. "XYZ Traders") stay *Others* until you save one with a category.
- **Receipt reading without Gemini** depends on photo quality; always check the fields before saving.
- **Online demo data** can be reset when the free server restarts.
