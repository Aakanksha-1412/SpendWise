# SPENDWISE — Autonomous Personal Financial Expense & Budgeting Assistant

An Agentic AI personal financial expense and budgeting assistant built with **Python 3.10+**, **Streamlit**, **LangChain / LangGraph**, **SQLite3**, **Pandas**, **Tesseract OCR / Vision LLM**, **ChromaDB**, and **Plotly**.

---

## 1. Project Overview & Agentic Concept

Unlike basic CRUD expense trackers with a bolted-on chatbot, **SpendWise** is designed around an **Agentic AI Orchestrator** (`agent/graph.py`). When a user submits a natural-language request, CSV statement, or receipt image, the central LangGraph controller:

1. **Understands the Request** (`understand_request_node`)
2. **Decides Required Tool(s)** (`decide_required_tool_node`)
3. **Calls Deterministic Tools** (`call_tool_node` -> OCR, Categorization, SQLite, Pandas Budget & Spike Detector)
4. **Evaluates Results** (`evaluate_result_node` -> checks overruns, thresholds, and discretionary buffers)
5. **Generates Final Response / Alert / Suggestion** (`generate_response_node`)

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
│   └── assistant.py              # Ask SpendWise AI chat interface with LangGraph trace viewer
│
├── agent/                        # Member 1: LangGraph Agentic Orchestrator
│   ├── graph.py                  # StateGraph nodes (Understand -> Route -> Call -> Evaluate -> Respond)
│   ├── state.py                  # TypedDict AgentState schema
│   └── prompts.py                # System instructions & intent classification prompts
│
├── tools/                        # Deterministic Agent & UI Tools
│   ├── ocr_tool.py               # Member 4: Receipt image -> Merchant, Date, Items, Tax, Total
│   ├── database_tool.py          # Member 2: SQLite CRUD & query interfaces
│   ├── categorization_tool.py    # Member 2: Auto-categorization & NL expense parser
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
├── assets/                       # Static logos or sample receipt test images
├── .env.example                  # Environment variable template (Never commit real keys)
├── .gitignore                    # Git ignore rules for Python, SQLite, and .env
├── requirements.txt              # Python package dependencies
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
Edit `.env` and add your `GEMINI_API_KEY` (or leave default to run in deterministic offline demo mode).

### Step 4: Run the Streamlit Application
```bash
streamlit run app.py
```

---

## 5. Future Integration Points for Team Members

1. **OCR Integration (`tools/ocr_tool.py`)**: Replace the demo receipt dictionary with `pytesseract.image_to_string(Image.open(image_file))` or Gemini Vision structured output.
2. **ChromaDB Semantic Memory (`tools/categorization_tool.py`)**: Store past `(merchant, description) -> category` embeddings in ChromaDB so recurring college merchants auto-categorize with high accuracy.
3. **LLM Reasoning in LangGraph (`agent/graph.py`)**: Bind `ChatGoogleGenerativeAI(model="gemini-2.5-flash")` inside `understand_request_node` and `generate_response_node` while keeping `call_tool_node` 100% deterministic Python/Pandas.
