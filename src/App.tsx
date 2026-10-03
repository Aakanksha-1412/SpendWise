import React, { useState, useMemo } from "react";
import {
  LayoutDashboard,
  FileSpreadsheet,
  Upload,
  Target,
  BarChart3,
  Bot,
  FolderCode,
  Wallet,
} from "lucide-react";
import {
  CategoryName,
  PageId,
  Transaction,
} from "./types/spendwise";
import {
  detectAllCategorySpikes,
  getAllBudgetStatuses,
  INITIAL_BUDGETS,
  INITIAL_TRANSACTIONS,
  suggestDiscretionaryReallocation,
} from "./services/spendwiseEngine";
import { HomePage } from "./components/HomePage";
import { TransactionsPage } from "./components/TransactionsPage";
import { UploadPage } from "./components/UploadPage";
import { BudgetPage } from "./components/BudgetPage";
import { AnalyticsPage } from "./components/AnalyticsPage";
import { AssistantPage } from "./components/AssistantPage";
import { TeamArchitecturePage } from "./components/TeamArchitecturePage";

export default function App() {
  const [activePage, setActivePage] = useState<PageId>("home");
  const [transactions, setTransactions] =
    useState<Transaction[]>(INITIAL_TRANSACTIONS);
  const [budgets, setBudgets] =
    useState<Record<CategoryName, number>>(INITIAL_BUDGETS);

  const statuses = useMemo(
    () => getAllBudgetStatuses(transactions, budgets, "2026-10"),
    [transactions, budgets]
  );

  const spikes = useMemo(
    () => detectAllCategorySpikes(transactions),
    [transactions]
  );

  const reallocation = useMemo(
    () => suggestDiscretionaryReallocation(statuses),
    [statuses]
  );

  const handleAddTransaction = (
    tx: Omit<Transaction, "id" | "createdAt">
  ): Transaction => {
    const newTx: Transaction = {
      ...tx,
      id: Date.now() + Math.floor(Math.random() * 1000),
      createdAt: new Date().toISOString().slice(0, 19).replace("T", " "),
    };
    setTransactions((prev) => [newTx, ...prev]);
    return newTx;
  };

  const handleBulkAddTransactions = (
    txs: Array<Omit<Transaction, "id" | "createdAt">>
  ) => {
    const baseId = Date.now();
    const created: Transaction[] = txs.map((tx, idx) => ({
      ...tx,
      id: baseId + idx,
      createdAt: new Date().toISOString().slice(0, 19).replace("T", " "),
    }));
    setTransactions((prev) => [...created, ...prev]);
  };

  const navItems: Array<{
    id: PageId;
    label: string;
    pyFile: string;
    icon: React.ReactNode;
  }> = [
    {
      id: "home",
      label: "Home",
      pyFile: "pages/home.py",
      icon: <LayoutDashboard className="w-4 h-4" />,
    },
    {
      id: "transactions",
      label: "Transactions",
      pyFile: "pages/transactions.py",
      icon: <FileSpreadsheet className="w-4 h-4" />,
    },
    {
      id: "upload",
      label: "Upload Expense",
      pyFile: "pages/upload.py",
      icon: <Upload className="w-4 h-4" />,
    },
    {
      id: "budget",
      label: "Budget",
      pyFile: "pages/budget.py",
      icon: <Target className="w-4 h-4" />,
    },
    {
      id: "analytics",
      label: "Analytics",
      pyFile: "pages/analytics.py",
      icon: <BarChart3 className="w-4 h-4" />,
    },
    {
      id: "assistant",
      label: "AI Assistant",
      pyFile: "pages/assistant.py",
      icon: <Bot className="w-4 h-4" />,
    },
    {
      id: "architecture",
      label: "Python Code & Team",
      pyFile: "SpendWise/*",
      icon: <FolderCode className="w-4 h-4" />,
    },
  ];

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-slate-50 text-slate-900">
      {/* Left Multipage Navigation Sidebar (Streamlit Multipage Architecture) */}
      <aside className="w-full lg:w-64 bg-white border-b lg:border-b-0 lg:border-r border-slate-200 shrink-0 flex flex-col justify-between">
        <div className="p-5 space-y-6">
          {/* Brand Lockup */}
          <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
            <div className="p-2 rounded-lg bg-slate-900 text-white">
              <Wallet className="w-4 h-4" />
            </div>
            <div>
              <div className="text-base font-bold tracking-tight text-slate-900">
                SPENDWISE
              </div>
              <div className="text-xs text-slate-500">
                Agentic Finance Assistant
              </div>
            </div>
          </div>

          {/* Multipage Sidebar Links */}
          <nav className="space-y-1" aria-label="SpendWise Navigation">
            <div className="text-xs font-semibold text-slate-400 px-3 mb-2">
              Streamlit Pages (`st.navigation`)
            </div>
            {navItems.map((item) => {
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActivePage(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                    isActive
                      ? "bg-slate-900 text-white font-semibold"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  <span className="flex items-center gap-2.5 whitespace-nowrap">
                    {item.icon}
                    <span>{item.label}</span>
                  </span>
                  <span
                    className={`font-mono text-[10px] ${
                      isActive ? "text-teal-300" : "text-slate-400"
                    }`}
                  >
                    {item.pyFile.replace("pages/", "")}
                  </span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Team Project Architecture Summary in Sidebar Footer */}
        <div className="hidden lg:block p-5 border-t border-slate-100 space-y-2 text-xs text-slate-500">
          <div className="font-semibold text-slate-700">
            Official Tech Stack
          </div>
          <div className="leading-relaxed">
            Python 3.10+ · Streamlit · LangGraph · SQLite3 · Pandas · OCR ·
            ChromaDB · Plotly
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Clean 3-Zone Top Bar Contract */}
        <header className="bg-white border-b border-slate-200 px-6 py-3.5 flex items-center justify-between">
          {/* Zone 1: Single text element wordmark */}
          <button
            type="button"
            onClick={() => setActivePage("home")}
            className="text-sm font-bold tracking-tight text-slate-900 cursor-pointer whitespace-nowrap"
          >
            SPENDWISE
          </button>

          {/* Zone 2: 5 clean text navigation links */}
          <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-slate-600">
            <button
              type="button"
              onClick={() => setActivePage("home")}
              className={`hover:text-slate-900 transition-colors cursor-pointer whitespace-nowrap ${
                activePage === "home"
                  ? "text-slate-900 underline underline-offset-4"
                  : ""
              }`}
            >
              Home
            </button>
            <button
              type="button"
              onClick={() => setActivePage("transactions")}
              className={`hover:text-slate-900 transition-colors cursor-pointer whitespace-nowrap ${
                activePage === "transactions"
                  ? "text-slate-900 underline underline-offset-4"
                  : ""
              }`}
            >
              Transactions
            </button>
            <button
              type="button"
              onClick={() => setActivePage("upload")}
              className={`hover:text-slate-900 transition-colors cursor-pointer whitespace-nowrap ${
                activePage === "upload"
                  ? "text-slate-900 underline underline-offset-4"
                  : ""
              }`}
            >
              Upload
            </button>
            <button
              type="button"
              onClick={() => setActivePage("budget")}
              className={`hover:text-slate-900 transition-colors cursor-pointer whitespace-nowrap ${
                activePage === "budget"
                  ? "text-slate-900 underline underline-offset-4"
                  : ""
              }`}
            >
              Budget
            </button>
            <button
              type="button"
              onClick={() => setActivePage("analytics")}
              className={`hover:text-slate-900 transition-colors cursor-pointer whitespace-nowrap ${
                activePage === "analytics"
                  ? "text-slate-900 underline underline-offset-4"
                  : ""
              }`}
            >
              Analytics
            </button>
          </nav>

          {/* Zone 3: Primary actions */}
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setActivePage("architecture")}
              className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors whitespace-nowrap cursor-pointer"
            >
              Python Files (23)
            </button>
            <button
              type="button"
              onClick={() => setActivePage("assistant")}
              className="px-3.5 py-1.5 text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 rounded-lg transition-colors whitespace-nowrap cursor-pointer"
            >
              Ask SpendWise
            </button>
          </div>
        </header>

        {/* Active Page Viewport */}
        <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto">
          {activePage === "home" && (
            <HomePage
              statuses={statuses}
              spikes={spikes}
              suggestions={reallocation.suggestions}
              onNavigate={setActivePage}
            />
          )}

          {activePage === "transactions" && (
            <TransactionsPage
              transactions={transactions}
              onAddTransaction={handleAddTransaction}
            />
          )}

          {activePage === "upload" && (
            <UploadPage
              onBulkAddTransactions={handleBulkAddTransactions}
              onAddTransaction={handleAddTransaction}
            />
          )}

          {activePage === "budget" && (
            <BudgetPage
              statuses={statuses}
              budgets={budgets}
              onUpdateBudgets={setBudgets}
            />
          )}

          {activePage === "analytics" && (
            <AnalyticsPage
              statuses={statuses}
              spikes={spikes}
              transactions={transactions}
            />
          )}

          {activePage === "assistant" && (
            <AssistantPage
              transactions={transactions}
              budgets={budgets}
              onAddTransaction={handleAddTransaction}
            />
          )}

          {activePage === "architecture" && <TeamArchitecturePage />}
        </main>
      </div>
    </div>
  );
}
