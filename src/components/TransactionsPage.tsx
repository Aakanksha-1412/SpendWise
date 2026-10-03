import React, { useState, useMemo } from "react";
import { Plus, Search, Sparkles, Filter, RotateCcw } from "lucide-react";
import {
  CategoryName,
  ExpenseSource,
  Transaction,
} from "../types/spendwise";
import {
  CATEGORIES,
  categorizeExpense,
  formatINR,
  normalizeToDisplayDate,
  parseNaturalLanguageExpense,
} from "../services/spendwiseEngine";

interface TransactionsPageProps {
  transactions: Transaction[];
  onAddTransaction: (tx: Omit<Transaction, "id" | "createdAt">) => void;
}

export const TransactionsPage: React.FC<TransactionsPageProps> = ({
  transactions,
  onAddTransaction,
}) => {
  // Filter state
  const [categoryFilter, setCategoryFilter] = useState<string>("All");
  const [merchantFilter, setMerchantFilter] = useState<string>("");
  const [dateFilter, setDateFilter] = useState<string>("");

  // Add Expense mode: Natural Language vs Structured Form
  const [entryMode, setEntryMode] = useState<"nl" | "form">("nl");
  const [nlText, setNlText] = useState<string>("");
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  // Manual form fields
  const [dateInput, setDateInput] = useState<string>("2026-10-08");
  const [merchantInput, setMerchantInput] = useState<string>("");
  const [amountInput, setAmountInput] = useState<string>("");
  const [categoryInput, setCategoryInput] = useState<string>("Auto-Detect");
  const [descInput, setDescInput] = useState<string>("");

  const handleNaturalLanguageSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!nlText.trim()) return;
    const parsed = parseNaturalLanguageExpense(nlText);
    if (parsed.amount <= 0) {
      setFeedbackMsg(
        "Please include a valid amount in your sentence (e.g., 'Spent ₹450 at Swiggy for dinner')."
      );
      return;
    }
    const { display, iso } = normalizeToDisplayDate(parsed.date);
    onAddTransaction({
      date: display,
      isoDate: iso,
      merchant: parsed.merchant,
      amount: parsed.amount,
      category: parsed.category,
      description: parsed.description,
      source: "Text",
    });
    setFeedbackMsg(
      `Added ${formatINR(parsed.amount)} at ${parsed.merchant} → Auto-Categorized as ${parsed.category} (Saved via tools/database_tool.py)`
    );
    setNlText("");
  };

  const handleStructuredSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const amt = parseFloat(amountInput);
    if (!merchantInput.trim() || isNaN(amt) || amt <= 0) {
      setFeedbackMsg("Please enter a valid merchant name and positive amount.");
      return;
    }
    const assignedCategory: CategoryName =
      categoryInput === "Auto-Detect"
        ? categorizeExpense(merchantInput, descInput)
        : (categoryInput as CategoryName);

    const { display, iso } = normalizeToDisplayDate(dateInput);
    onAddTransaction({
      date: display,
      isoDate: iso,
      merchant: merchantInput.trim(),
      amount: amt,
      category: assignedCategory,
      description: descInput.trim() || "Expense entry",
      source: "Text" as ExpenseSource,
    });
    setFeedbackMsg(
      `Saved ${formatINR(amt)} at ${merchantInput.trim()} (${assignedCategory}) to SQLite ledger.`
    );
    setMerchantInput("");
    setAmountInput("");
    setDescInput("");
  };

  const filteredTransactions = useMemo(() => {
    return transactions.filter((tx) => {
      if (categoryFilter !== "All" && tx.category !== categoryFilter) {
        return false;
      }
      if (
        merchantFilter.trim() &&
        !tx.merchant.toLowerCase().includes(merchantFilter.trim().toLowerCase()) &&
        !tx.description
          .toLowerCase()
          .includes(merchantFilter.trim().toLowerCase())
      ) {
        return false;
      }
      if (dateFilter.trim()) {
        const norm = normalizeToDisplayDate(dateFilter.trim());
        if (
          tx.date !== dateFilter.trim() &&
          tx.isoDate !== dateFilter.trim() &&
          tx.date !== norm.display
        ) {
          return false;
        }
      }
      return true;
    });
  }, [transactions, categoryFilter, merchantFilter, dateFilter]);

  const totalFilteredAmount = filteredTransactions.reduce(
    (sum, t) => sum + t.amount,
    0
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <p className="text-xs font-medium text-teal-700">
            02. SQLite Transactions Ledger · `pages/transactions.py`
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">
            Transactions
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            All database reads and writes route through{" "}
            <code className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded">
              tools/database_tool.py
            </code>{" "}
            and{" "}
            <code className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded">
              tools/categorization_tool.py
            </code>
            .
          </p>
        </div>
      </div>

      {/* Add Expense Section */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Add Expense
            </h2>
            <p className="text-xs text-slate-500">
              Enter expenses using natural language text or structured fields
            </p>
          </div>
          <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg self-start">
            <button
              type="button"
              onClick={() => setEntryMode("nl")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
                entryMode === "nl"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Natural Language Input
            </button>
            <button
              type="button"
              onClick={() => setEntryMode("form")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer whitespace-nowrap ${
                entryMode === "form"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Structured Form
            </button>
          </div>
        </div>

        {entryMode === "nl" ? (
          <form
            onSubmit={handleNaturalLanguageSubmit}
            className="flex flex-col sm:flex-row gap-3"
          >
            <div className="relative flex-1">
              <Sparkles className="w-4 h-4 text-teal-700 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={nlText}
                onChange={(e) => setNlText(e.target.value)}
                placeholder='e.g. "Spent ₹450 at Swiggy for dinner on 01-10-2026" or "Paid ₹340 to Uber for college commute"'
                className="w-full pl-10 pr-4 py-2.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:border-teal-700"
              />
            </div>
            <button
              type="submit"
              className="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 whitespace-nowrap cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Parse &amp; Add Expense
            </button>
          </form>
        ) : (
          <form
            onSubmit={handleStructuredSubmit}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3 items-end"
          >
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Date
              </label>
              <input
                type="date"
                value={dateInput}
                onChange={(e) => setDateInput(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Merchant
              </label>
              <input
                type="text"
                value={merchantInput}
                onChange={(e) => setMerchantInput(e.target.value)}
                placeholder="Swiggy, Uber, Amazon..."
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Amount (₹)
              </label>
              <input
                type="number"
                min="1"
                step="any"
                value={amountInput}
                onChange={(e) => setAmountInput(e.target.value)}
                placeholder="450"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Category
              </label>
              <select
                value={categoryInput}
                onChange={(e) => setCategoryInput(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg bg-white"
              >
                <option value="Auto-Detect">Auto-Detect Category</option>
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Description
              </label>
              <input
                type="text"
                value={descInput}
                onChange={(e) => setDescInput(e.target.value)}
                placeholder="Dinner / Shoes / Ride"
                className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg transition-colors h-[38px] whitespace-nowrap cursor-pointer"
            >
              Add Transaction
            </button>
          </form>
        )}

        {feedbackMsg && (
          <div className="text-xs text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3.5 py-2">
            {feedbackMsg}
          </div>
        )}
      </div>

      {/* Filter Controls: Category, Date, Merchant */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Filter className="w-4 h-4 text-slate-500" />
            <span>Filter Transactions</span>
          </div>
          {(categoryFilter !== "All" || merchantFilter || dateFilter) && (
            <button
              type="button"
              onClick={() => {
                setCategoryFilter("All");
                setMerchantFilter("");
                setDateFilter("");
              }}
              className="text-xs text-slate-600 hover:text-slate-900 flex items-center gap-1 cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset Filters
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Category Filter
            </label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg bg-white"
            >
              <option value="All">All Categories (8)</option>
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Merchant / Description Filter
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={merchantFilter}
                onChange={(e) => setMerchantFilter(e.target.value)}
                placeholder="Swiggy, Uber, Amazon..."
                className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Date Filter (DD-MM-YYYY)
            </label>
            <input
              type="text"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              placeholder="e.g. 01-10-2026 or 02-10-2026"
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg font-mono"
            />
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="text-sm font-semibold text-slate-900">
            Transaction Records ({filteredTransactions.length})
          </div>
          <div className="text-xs text-slate-600">
            Filtered Total:{" "}
            <strong className="font-mono tabular-nums text-slate-900">
              {formatINR(totalFilteredAmount)}
            </strong>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-semibold text-slate-600">
                <th className="py-3 px-5">Date</th>
                <th className="py-3 px-5">Merchant</th>
                <th className="py-3 px-5 text-right">Amount</th>
                <th className="py-3 px-5">Category</th>
                <th className="py-3 px-5">Description</th>
                <th className="py-3 px-5">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 text-sm">
              {filteredTransactions.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="py-10 text-center text-sm text-slate-500"
                  >
                    No transactions match your current filter criteria.
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((tx) => (
                  <tr
                    key={tx.id}
                    className="hover:bg-slate-50/80 transition-colors"
                  >
                    <td className="py-3 px-5 font-mono tabular-nums text-xs text-slate-600 whitespace-nowrap">
                      {tx.date}
                    </td>
                    <td className="py-3 px-5 font-medium text-slate-900 whitespace-nowrap">
                      {tx.merchant}
                    </td>
                    <td className="py-3 px-5 text-right font-mono tabular-nums font-semibold text-slate-900 whitespace-nowrap">
                      {formatINR(tx.amount)}
                    </td>
                    <td className="py-3 px-5 text-xs text-slate-700 whitespace-nowrap">
                      {tx.category}
                    </td>
                    <td className="py-3 px-5 text-xs text-slate-600">
                      {tx.description}
                    </td>
                    <td className="py-3 px-5 text-xs font-mono text-slate-500 whitespace-nowrap">
                      {tx.source}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
