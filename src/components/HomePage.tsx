import React from "react";
import {
  PlusCircle,
  Upload,
  FileSpreadsheet,
  Target,
  BarChart3,
  Bot,
  AlertTriangle,
  Lightbulb,
  TrendingUp,
  ArrowRight,
} from "lucide-react";
import {
  CategoryBudgetStatus,
  PageId,
  SpendingSpike,
} from "../types/spendwise";
import { formatINR } from "../services/spendwiseEngine";

interface HomePageProps {
  statuses: CategoryBudgetStatus[];
  spikes: SpendingSpike[];
  suggestions: string[];
  onNavigate: (page: PageId) => void;
}

export const HomePage: React.FC<HomePageProps> = ({
  statuses,
  spikes,
  suggestions,
  onNavigate,
}) => {
  const totalBudget = statuses.reduce((acc, s) => acc + s.budget, 0);
  const totalSpent = statuses.reduce((acc, s) => acc + s.spent, 0);
  const remainingBudget = totalBudget - totalSpent;
  const overBudgetList = statuses.filter((s) => s.status === "OVER BUDGET");
  const activeSpikes = spikes.filter((s) => s.spikeDetected);
  const totalAlerts = overBudgetList.length + activeSpikes.length;

  const maxChartVal = Math.max(
    ...statuses.map((s) => Math.max(s.budget, s.spent)),
    6500
  );

  const quickActions: Array<{
    label: string;
    subtext: string;
    target: PageId;
    icon: React.ReactNode;
    primary?: boolean;
  }> = [
    {
      label: "Add Expense",
      subtext: "Text or manual entry",
      target: "transactions",
      icon: <PlusCircle className="w-4 h-4 text-teal-700" />,
    },
    {
      label: "Upload Receipt",
      subtext: "OCR & CSV ingestion",
      target: "upload",
      icon: <Upload className="w-4 h-4 text-sky-700" />,
    },
    {
      label: "View Transactions",
      subtext: "SQLite ledger & filters",
      target: "transactions",
      icon: <FileSpreadsheet className="w-4 h-4 text-slate-700" />,
    },
    {
      label: "Manage Budget",
      subtext: "8 category limits",
      target: "budget",
      icon: <Target className="w-4 h-4 text-amber-700" />,
    },
    {
      label: "View Analytics",
      subtext: "Trends & spike detector",
      target: "analytics",
      icon: <BarChart3 className="w-4 h-4 text-indigo-700" />,
    },
    {
      label: "Ask SpendWise",
      subtext: "LangGraph AI Agent",
      target: "assistant",
      icon: <Bot className="w-4 h-4 text-white" />,
      primary: true,
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-5 border-b border-slate-200">
        <div>
          <p className="text-xs font-medium text-teal-700 tracking-wide">
            01. Executive Financial Dashboard · October 2026 Cycle
          </p>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 mt-1">
            SPENDWISE
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Autonomous Personal Financial Expense &amp; Budgeting Assistant
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>SQLite3 Connected</span>
          <span aria-hidden="true">·</span>
          <span>Pandas Engine Active</span>
          <span aria-hidden="true">·</span>
          <span>LangGraph Orchestrator</span>
        </div>
      </div>

      {/* Clickable Navigation Cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-800">
            Quick Action Navigation
          </h2>
          <span className="text-xs text-slate-500">
            Click any module card to navigate directly
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {quickActions.map((item) => (
            <button
              key={item.label}
              onClick={() => onNavigate(item.target)}
              className={`group text-left p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                item.primary
                  ? "bg-slate-900 border-slate-900 text-white hover:bg-slate-800"
                  : "bg-white border-slate-200 text-slate-900 hover:border-slate-300 hover:bg-slate-50/70"
              }`}
            >
              <div className="flex items-center justify-between w-full mb-2.5">
                <div
                  className={`p-2 rounded-lg ${
                    item.primary ? "bg-white/10" : "bg-slate-100"
                  }`}
                >
                  {item.icon}
                </div>
                <ArrowRight
                  className={`w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5 ${
                    item.primary ? "text-slate-300" : "text-slate-400"
                  }`}
                />
              </div>
              <div>
                <div className="text-sm font-semibold whitespace-nowrap">
                  {item.label}
                </div>
                <div
                  className={`text-xs mt-0.5 truncate ${
                    item.primary ? "text-slate-300" : "text-slate-500"
                  }`}
                >
                  {item.subtext}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* 4 Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-500">Total Spent</div>
          <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums mt-1.5">
            {formatINR(totalSpent)}
          </div>
          <div className="text-xs text-slate-500 mt-2">
            October 2026 · {Math.round((totalSpent / totalBudget) * 100)}% of
            monthly budget
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-500">
            Monthly Budget
          </div>
          <div className="text-2xl font-bold text-slate-900 font-mono tabular-nums mt-1.5">
            {formatINR(totalBudget)}
          </div>
          <div className="text-xs text-slate-500 mt-2">
            Allocated across 8 official categories
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-500">
            Remaining Budget
          </div>
          <div
            className={`text-2xl font-bold font-mono tabular-nums mt-1.5 ${
              remainingBudget >= 0 ? "text-emerald-600" : "text-red-600"
            }`}
          >
            {formatINR(remainingBudget)}
          </div>
          <div className="text-xs text-slate-500 mt-2">
            Net available monthly buffer
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <div className="text-xs font-medium text-slate-500">
            Budget Alerts
          </div>
          <div
            className={`text-2xl font-bold font-mono tabular-nums mt-1.5 ${
              totalAlerts > 0 ? "text-red-600" : "text-emerald-600"
            }`}
          >
            {totalAlerts} Active
          </div>
          <div className="text-xs text-slate-500 mt-2">
            {overBudgetList.length} category overrun · {activeSpikes.length}{" "}
            weekly spike
          </div>
        </div>
      </div>

      {/* Main Split: Budget vs Actual Chart + AI Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Budget vs Actual Chart (Plotly equivalent view) */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Budget vs Actual Spending
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Computed via Pandas (`analytics/analytics.py`) · October 2026
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-600">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-xs bg-slate-300 inline-block" />
                Monthly Budget
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-xs bg-teal-700 inline-block" />
                Within Budget
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-xs bg-red-600 inline-block" />
                Over Budget
              </span>
            </div>
          </div>

          <div className="space-y-4">
            {statuses.map((item) => {
              const budgetWidth = Math.min(
                100,
                Math.round((item.budget / maxChartVal) * 100)
              );
              const spentWidth = Math.min(
                100,
                Math.round((item.spent / maxChartVal) * 100)
              );
              const isOver = item.status === "OVER BUDGET";

              return (
                <div key={item.category} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-800 w-28">
                      {item.category}
                    </span>
                    <div className="flex items-center gap-3 font-mono tabular-nums text-slate-600">
                      <span>Spent: {formatINR(item.spent)}</span>
                      <span aria-hidden="true">/</span>
                      <span>Budget: {formatINR(item.budget)}</span>
                      <span
                        className={`font-semibold ${
                          isOver ? "text-red-600" : "text-teal-700"
                        }`}
                      >
                        ({item.utilizationPct}%)
                      </span>
                    </div>
                  </div>

                  {/* Dual grouped horizontal bar */}
                  <div className="space-y-1">
                    <div className="w-full bg-slate-100 h-2 rounded-xs overflow-hidden">
                      <div
                        className="bg-slate-300 h-full rounded-xs transition-all"
                        style={{ width: `${budgetWidth}%` }}
                        title={`Budget: ${formatINR(item.budget)}`}
                      />
                    </div>
                    <div className="w-full bg-slate-100 h-2.5 rounded-xs overflow-hidden">
                      <div
                        className={`h-full rounded-xs transition-all ${
                          isOver ? "bg-red-600" : "bg-teal-700"
                        }`}
                        style={{ width: `${spentWidth}%` }}
                        title={`Actual Spent: ${formatINR(item.spent)}`}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* AI Insights & Alerts Panel */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 flex flex-col justify-between">
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                AI Insights &amp; Budget Alerts
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Generated from `tools/budget_tool.py` &amp; `tools/spike_detector.py`
              </p>
            </div>

            {/* Over Budget Alerts */}
            {overBudgetList.map((ob) => (
              <div
                key={ob.category}
                className="p-4 rounded-lg bg-red-50/80 border-l-4 border-red-600 space-y-1"
              >
                <div className="flex items-center gap-2 text-xs font-semibold text-red-900">
                  <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                  <span>🚨 {ob.category} Budget Alert</span>
                </div>
                <p className="text-xs text-red-800 leading-relaxed">
                  Your <strong>{ob.category}</strong> expenses (
                  <span className="font-mono">{formatINR(ob.spent)}</span>) have
                  exceeded your monthly budget (
                  <span className="font-mono">{formatINR(ob.budget)}</span>) by{" "}
                  <strong className="font-mono">
                    {formatINR(Math.abs(ob.remaining))}
                  </strong>
                  .
                </p>
              </div>
            ))}

            {/* Weekly Spike Alerts */}
            {activeSpikes.map((sp) => (
              <div
                key={sp.category}
                className="p-4 rounded-lg bg-amber-50/80 border-l-4 border-amber-600 space-y-1"
              >
                <div className="flex items-center gap-2 text-xs font-semibold text-amber-900">
                  <TrendingUp className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>
                    🚨 Spending Spike Detected — {sp.category} (+
                    {sp.increasePct}%)
                  </span>
                </div>
                <p className="text-xs text-amber-800 leading-relaxed">
                  Previous weekly {sp.category} spending:{" "}
                  <strong className="font-mono">
                    {formatINR(sp.previousWeeklySpending)}
                  </strong>{" "}
                  · Current weekly {sp.category} spending:{" "}
                  <strong className="font-mono">
                    {formatINR(sp.currentWeeklySpending)}
                  </strong>
                  .
                </p>
              </div>
            ))}

            {/* SpendWise Discretionary Suggestion */}
            {suggestions.map((sug, i) => (
              <div
                key={i}
                className="p-4 rounded-lg bg-emerald-50/80 border-l-4 border-emerald-600 space-y-1"
              >
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-900">
                  <Lightbulb className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>💡 SpendWise Suggestion</span>
                </div>
                <p className="text-xs text-emerald-800 leading-relaxed">
                  {sug}
                </p>
              </div>
            ))}
          </div>

          <div className="pt-4 mt-4 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Need deeper category reallocation advice?
            </span>
            <button
              onClick={() => onNavigate("assistant")}
              className="text-xs font-semibold text-teal-700 hover:text-teal-800 flex items-center gap-1 cursor-pointer"
            >
              Ask SpendWise Agent
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Category Overview Grid (All 8 Official Categories) */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-slate-900">
            Category Overview
          </h2>
          <span className="text-xs text-slate-500">
            Food · Transport · Shopping · Entertainment · Bills · Healthcare ·
            Education · Others
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statuses.map((cat) => {
            const isOver = cat.status === "OVER BUDGET";
            const isNear = cat.status === "NEAR LIMIT";
            return (
              <div
                key={cat.category}
                className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-900">
                      {cat.category}
                    </h3>
                    <span
                      className={`text-xs font-semibold ${
                        isOver
                          ? "text-red-600"
                          : isNear
                          ? "text-amber-600"
                          : "text-emerald-600"
                      }`}
                    >
                      {cat.status}
                    </span>
                  </div>
                  <div className="mt-3 space-y-1 text-xs text-slate-600 font-mono tabular-nums">
                    <div className="flex justify-between">
                      <span className="font-sans text-slate-500">Budget:</span>
                      <span>{formatINR(cat.budget)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-sans text-slate-500">Spent:</span>
                      <span className="font-semibold text-slate-900">
                        {formatINR(cat.spent)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="font-sans text-slate-500">
                        Remaining:
                      </span>
                      <span
                        className={`font-semibold ${
                          isOver ? "text-red-600" : "text-emerald-600"
                        }`}
                      >
                        {formatINR(cat.remaining)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-2.5 border-t border-slate-100">
                  <div className="w-full bg-slate-100 h-1.5 rounded-xs overflow-hidden">
                    <div
                      className={`h-full ${
                        isOver
                          ? "bg-red-600"
                          : isNear
                          ? "bg-amber-500"
                          : "bg-teal-700"
                      }`}
                      style={{
                        width: `${Math.min(100, cat.utilizationPct)}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
