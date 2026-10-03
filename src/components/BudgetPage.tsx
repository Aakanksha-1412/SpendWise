import React, { useState } from "react";
import { Save, CheckCircle2, AlertTriangle } from "lucide-react";
import {
  CategoryBudgetStatus,
  CategoryName,
} from "../types/spendwise";
import { formatINR } from "../services/spendwiseEngine";

interface BudgetPageProps {
  statuses: CategoryBudgetStatus[];
  budgets: Record<CategoryName, number>;
  onUpdateBudgets: (updated: Record<CategoryName, number>) => void;
}

export const BudgetPage: React.FC<BudgetPageProps> = ({
  statuses,
  budgets,
  onUpdateBudgets,
}) => {
  const [draftBudgets, setDraftBudgets] =
    useState<Record<CategoryName, number>>(budgets);
  const [savedBanner, setSavedBanner] = useState<boolean>(false);

  const handleBudgetChange = (category: CategoryName, val: string) => {
    const parsed = parseFloat(val);
    setDraftBudgets((prev) => ({
      ...prev,
      [category]: isNaN(parsed) || parsed < 0 ? 0 : parsed,
    }));
    setSavedBanner(false);
  };

  const handleSaveAll = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateBudgets(draftBudgets);
    setSavedBanner(true);
  };

  const totalBudget = statuses.reduce((a, b) => a + b.budget, 0);
  const totalSpent = statuses.reduce((a, b) => a + b.spent, 0);
  const totalRemaining = totalBudget - totalSpent;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <p className="text-xs font-medium text-teal-700">
            04. Monthly Category Budgets · `pages/budget.py` &amp; `tools/budget_tool.py`
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">
            Monthly Budget Manager
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Define monthly limits across all 8 official categories and compare
            with actual SQLite spending using Pandas.
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono tabular-nums bg-white border border-slate-200 px-4 py-2.5 rounded-xl">
          <span>
            Total Budget: <strong>{formatINR(totalBudget)}</strong>
          </span>
          <span aria-hidden="true">·</span>
          <span>
            Total Spent: <strong>{formatINR(totalSpent)}</strong>
          </span>
          <span aria-hidden="true">·</span>
          <span
            className={
              totalRemaining >= 0
                ? "text-emerald-700 font-semibold"
                : "text-red-600 font-semibold"
            }
          >
            Remaining: {formatINR(totalRemaining)}
          </span>
        </div>
      </div>

      {/* Category Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statuses.map((item) => {
          const isOver = item.status === "OVER BUDGET";
          const isNear = item.status === "NEAR LIMIT";

          return (
            <div
              key={item.category}
              className={`bg-white rounded-xl p-5 border transition-all flex flex-col justify-between ${
                isOver ? "border-red-300" : "border-slate-200"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-base font-bold text-slate-900">
                    {item.category}
                  </h2>
                  <span
                    className={`text-xs font-semibold ${
                      isOver
                        ? "text-red-600"
                        : isNear
                        ? "text-amber-600"
                        : "text-emerald-600"
                    }`}
                  >
                    {item.status}
                  </span>
                </div>

                <div className="space-y-1.5 text-xs font-mono tabular-nums border-t border-slate-100 pt-3">
                  <div className="flex justify-between">
                    <span className="font-sans text-slate-500">Budget:</span>
                    <span className="text-slate-900 font-medium">
                      {formatINR(item.budget)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-sans text-slate-500">Spent:</span>
                    <span className="text-slate-900 font-semibold">
                      {formatINR(item.spent)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-sans text-slate-500">Remaining:</span>
                    <span
                      className={`font-bold ${
                        isOver ? "text-red-600" : "text-emerald-600"
                      }`}
                    >
                      {formatINR(item.remaining)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 space-y-1.5">
                <div className="flex justify-between text-xs text-slate-500">
                  <span>Utilization</span>
                  <span className="font-mono">{item.utilizationPct}%</span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-xs overflow-hidden">
                  <div
                    className={`h-full ${
                      isOver
                        ? "bg-red-600"
                        : isNear
                        ? "bg-amber-500"
                        : "bg-teal-700"
                    }`}
                    style={{
                      width: `${Math.min(100, item.utilizationPct)}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Configure Monthly Budgets Form */}
      <form
        onSubmit={handleSaveAll}
        className="bg-white border border-slate-200 rounded-xl p-6 space-y-5"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Define / Adjust Monthly Category Budgets (October 2026)
            </h2>
            <p className="text-xs text-slate-500">
              Updates the `budgets` table in SQLite via{" "}
              <code className="font-mono">tools/database_tool.py :: upsert_budget</code>
            </p>
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg flex items-center gap-2 self-start cursor-pointer whitespace-nowrap"
          >
            <Save className="w-3.5 h-3.5" />
            Save Monthly Budgets
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statuses.map((item) => (
            <div key={item.category}>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                {item.category} Monthly Budget (₹)
              </label>
              <input
                type="number"
                min="0"
                step="100"
                value={draftBudgets[item.category]}
                onChange={(e) =>
                  handleBudgetChange(item.category, e.target.value)
                }
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg font-mono tabular-nums focus:outline-none focus:border-teal-700"
              />
            </div>
          ))}
        </div>

        {savedBanner && (
          <div className="flex items-center gap-2 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg px-3.5 py-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>
              Monthly budgets updated in SQLite and recalculated across all
              Pandas charts!
            </span>
          </div>
        )}
      </form>

      {/* Budget Summary Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-900">
            Budget vs Actual Ledger (`calculate_budget_status`)
          </h3>
          <span className="text-xs text-slate-500">
            Team Member 4 · `tools/budget_tool.py`
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold text-slate-600">
                <th className="py-3 px-5">Category</th>
                <th className="py-3 px-5 text-right">Budget</th>
                <th className="py-3 px-5 text-right">Spent</th>
                <th className="py-3 px-5 text-right">Remaining</th>
                <th className="py-3 px-5 text-right">Utilization</th>
                <th className="py-3 px-5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {statuses.map((s) => {
                const isOver = s.status === "OVER BUDGET";
                return (
                  <tr key={s.category} className="hover:bg-slate-50/70">
                    <td className="py-3 px-5 font-medium text-slate-900">
                      {s.category}
                    </td>
                    <td className="py-3 px-5 text-right font-mono tabular-nums text-slate-700">
                      {formatINR(s.budget)}
                    </td>
                    <td className="py-3 px-5 text-right font-mono tabular-nums font-medium text-slate-900">
                      {formatINR(s.spent)}
                    </td>
                    <td
                      className={`py-3 px-5 text-right font-mono tabular-nums font-semibold ${
                        isOver ? "text-red-600" : "text-emerald-600"
                      }`}
                    >
                      {formatINR(s.remaining)}
                    </td>
                    <td className="py-3 px-5 text-right font-mono tabular-nums text-xs text-slate-600">
                      {s.utilizationPct}%
                    </td>
                    <td className="py-3 px-5 text-xs font-semibold">
                      <span
                        className={
                          isOver
                            ? "text-red-600 flex items-center gap-1"
                            : s.status === "NEAR LIMIT"
                            ? "text-amber-600"
                            : "text-emerald-600"
                        }
                      >
                        {isOver && <AlertTriangle className="w-3.5 h-3.5" />}
                        {s.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
