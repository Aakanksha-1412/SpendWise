import React from "react";
import { AlertTriangle, TrendingUp } from "lucide-react";
import {
  CategoryBudgetStatus,
  SpendingSpike,
  Transaction,
} from "../types/spendwise";
import { CATEGORY_COLORS, formatINR } from "../services/spendwiseEngine";

interface AnalyticsPageProps {
  statuses: CategoryBudgetStatus[];
  spikes: SpendingSpike[];
  transactions: Transaction[];
}

export const AnalyticsPage: React.FC<AnalyticsPageProps> = ({
  statuses,
  spikes,
  transactions,
}) => {
  const totalOctoberSpent = statuses.reduce((a, b) => a + b.spent, 0);
  const septemberSpent = transactions
    .filter((t) => t.isoDate.startsWith("2026-09"))
    .reduce((a, b) => a + b.amount, 0);

  const sortedBySpend = [...statuses].sort((a, b) => b.spent - a.spent);
  const maxSpendOrBudget = Math.max(
    ...statuses.map((s) => Math.max(s.budget, s.spent)),
    6500
  );

  // Daily October spending trend aggregation
  const dailyTrend = React.useMemo(() => {
    const octTxs = transactions.filter((t) => t.isoDate.startsWith("2026-10"));
    const byDate: Record<string, number> = {};
    for (const tx of octTxs) {
      byDate[tx.isoDate] = (byDate[tx.isoDate] || 0) + tx.amount;
    }
    const sortedDates = Object.keys(byDate).sort();
    let cumulative = 0;
    return sortedDates.map((iso) => {
      const daily = byDate[iso];
      cumulative += daily;
      const dayLabel = iso.slice(8, 10) + " Oct";
      return {
        date: dayLabel,
        daily,
        cumulative,
      };
    });
  }, [transactions]);

  const maxCumulative = Math.max(
    ...dailyTrend.map((d) => d.cumulative),
    totalOctoberSpent,
    1000
  );

  const detectedSpikes = spikes.filter((s) => s.spikeDetected);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-slate-200">
        <p className="text-xs font-medium text-teal-700">
          05. Pandas Analytics &amp; Anomaly Detection · `pages/analytics.py`,{" "}
          `analytics/analytics.py` &amp; `tools/spike_detector.py`
        </p>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">
          Financial Analytics &amp; Spike Detection
        </h1>
        <p className="text-sm text-slate-600 mt-0.5">
          All calculations are performed by{" "}
          <code className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded">
            analytics/analytics.py
          </code>
          ,{" "}
          <code className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded">
            tools/budget_tool.py
          </code>
          , and{" "}
          <code className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded">
            tools/spike_detector.py
          </code>
          .
        </p>
      </div>

      {/* 6. SPENDING SPIKE DETECTION SECTION */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              6. Spending Spike Detection (`tools/spike_detector.py`)
            </h2>
            <p className="text-xs text-slate-500">
              Compares Previous Weekly Spending vs Current Weekly Spending across
              all categories
            </p>
          </div>
          <span className="text-xs font-mono text-red-600 font-semibold">
            {detectedSpikes.length} Spike(s) Flagged
          </span>
        </div>

        {detectedSpikes.map((sp) => (
          <div
            key={sp.category}
            className="p-4 rounded-xl bg-red-50/90 border-l-4 border-red-600 flex flex-col md:flex-row md:items-center justify-between gap-4"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-sm font-bold text-red-900">
                <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
                <span>🚨 Spending Spike Detected — {sp.category}</span>
              </div>
              <p className="text-xs text-red-800">{sp.message}</p>
            </div>

            <div className="flex items-center gap-5 font-mono tabular-nums text-xs bg-white/90 px-4 py-2.5 rounded-lg border border-red-200 shrink-0">
              <div>
                <div className="text-slate-500 font-sans">
                  Previous weekly {sp.category}:
                </div>
                <div className="text-sm font-bold text-slate-800">
                  {formatINR(sp.previousWeeklySpending)}
                </div>
              </div>
              <div className="text-slate-400">→</div>
              <div>
                <div className="text-slate-500 font-sans">
                  Current weekly {sp.category}:
                </div>
                <div className="text-sm font-bold text-red-600">
                  {formatINR(sp.currentWeeklySpending)} (+{sp.increasePct}%)
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ROW 1: 1. Category-wise Spending & 2. Budget vs Actual */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 1. Category-Wise Spending */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              1. Category-Wise Spending Breakdown
            </h2>
            <p className="text-xs text-slate-500">
              Share of total October 2026 spending ({formatINR(totalOctoberSpent)})
            </p>
          </div>

          <div className="space-y-3 pt-1">
            {sortedBySpend.map((item) => {
              const sharePct =
                totalOctoberSpent > 0
                  ? Math.round((item.spent / totalOctoberSpent) * 1000) / 10
                  : 0;
              return (
                <div key={item.category} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-800">
                      {item.category}
                    </span>
                    <span className="font-mono tabular-nums text-slate-700">
                      {formatINR(item.spent)} ({sharePct}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 h-2.5 rounded-xs overflow-hidden">
                    <div
                      className="h-full rounded-xs"
                      style={{
                        width: `${Math.min(100, sharePct * 2)}%`,
                        backgroundColor: CATEGORY_COLORS[item.category],
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 2. Budget vs Actual */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              2. Budget vs Actual Comparison
            </h2>
            <p className="text-xs text-slate-500">
              Monthly allocation vs cumulative actual expenditure
            </p>
          </div>

          <div className="space-y-3.5 pt-1">
            {statuses.map((item) => {
              const bPct = Math.round((item.budget / maxSpendOrBudget) * 100);
              const sPct = Math.round((item.spent / maxSpendOrBudget) * 100);
              const isOver = item.status === "OVER BUDGET";
              return (
                <div key={item.category} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-slate-800">
                      {item.category}
                    </span>
                    <span className="font-mono tabular-nums text-slate-600">
                      Actual {formatINR(item.spent)} / Budget{" "}
                      {formatINR(item.budget)}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1">
                    <div className="w-full bg-slate-100 h-2 rounded-xs">
                      <div
                        className="bg-slate-300 h-full rounded-xs"
                        style={{ width: `${bPct}%` }}
                      />
                    </div>
                    <div className="w-full bg-slate-100 h-2 rounded-xs">
                      <div
                        className={`h-full rounded-xs ${
                          isOver ? "bg-red-600" : "bg-teal-700"
                        }`}
                        style={{ width: `${sPct}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ROW 2: 3. Weekly Spending & 4. Monthly Spending */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 3. Weekly Spending Comparison */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              3. Weekly Spending Comparison
            </h2>
            <p className="text-xs text-slate-500">
              Previous Week (Sep 18–24) vs Current Week (Oct 01–08)
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-2.5 pr-3">Category</th>
                  <th className="py-2.5 px-3 text-right">Prev Week</th>
                  <th className="py-2.5 px-3 text-right">Current Week</th>
                  <th className="py-2.5 pl-3 text-right">Delta</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
                {spikes.map((sp) => (
                  <tr key={sp.category}>
                    <td className="py-2.5 pr-3 font-sans font-medium text-slate-900">
                      {sp.category}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-600">
                      {formatINR(sp.previousWeeklySpending)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-semibold text-slate-900">
                      {formatINR(sp.currentWeeklySpending)}
                    </td>
                    <td
                      className={`py-2.5 pl-3 text-right font-semibold ${
                        sp.spikeDetected ? "text-red-600" : "text-slate-600"
                      }`}
                    >
                      {sp.increaseAmount >= 0 ? "+" : ""}
                      {formatINR(sp.increaseAmount)} ({sp.increasePct}%)
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 4. Monthly Spending & 5. Spending Trends */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              4. Monthly Spending Comparison
            </h2>
            <p className="text-xs text-slate-500">
              Aggregate expenditure across active months
            </p>
            <div className="grid grid-cols-2 gap-4 mt-3">
              <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
                <div className="text-xs text-slate-500">September 2026</div>
                <div className="text-lg font-bold text-slate-800 font-mono tabular-nums mt-0.5">
                  {formatINR(septemberSpent)}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Baseline weekly cycle
                </div>
              </div>
              <div className="p-3.5 rounded-lg bg-teal-50/70 border border-teal-200">
                <div className="text-xs text-teal-800 font-medium">
                  October 2026 (Active)
                </div>
                <div className="text-lg font-bold text-teal-900 font-mono tabular-nums mt-0.5">
                  {formatINR(totalOctoberSpent)}
                </div>
                <div className="text-xs text-teal-700 mt-1">
                  15 transactions recorded
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-base font-semibold text-slate-900">
                  5. Daily &amp; Cumulative Spending Trends (Oct 2026)
                </h2>
                <p className="text-xs text-slate-500">
                  Daily transaction velocity and cumulative monthly burn
                </p>
              </div>
              <TrendingUp className="w-4 h-4 text-teal-700" />
            </div>

            <div className="space-y-2.5">
              {dailyTrend.map((d) => {
                const barPct = Math.min(
                  100,
                  Math.round((d.cumulative / maxCumulative) * 100)
                );
                return (
                  <div key={d.date} className="space-y-1">
                    <div className="flex justify-between text-xs font-mono tabular-nums">
                      <span className="text-slate-700 font-medium">
                        {d.date}
                      </span>
                      <span className="text-slate-600">
                        Daily: {formatINR(d.daily)} · Cumulative:{" "}
                        <strong className="text-slate-900">
                          {formatINR(d.cumulative)}
                        </strong>
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 h-2 rounded-xs overflow-hidden">
                      <div
                        className="bg-teal-700 h-full rounded-xs transition-all"
                        style={{ width: `${barPct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
