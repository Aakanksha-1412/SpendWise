import React, { useState } from "react";
import {
  FileSpreadsheet,
  Receipt,
  ArrowRight,
  CheckCircle2,
  UploadCloud,
  FileText,
} from "lucide-react";
import {
  CategoryName,
  ExtractedReceipt,
  Transaction,
} from "../types/spendwise";
import {
  CATEGORIES,
  categorizeExpense,
  formatINR,
  normalizeToDisplayDate,
} from "../services/spendwiseEngine";

interface UploadPageProps {
  onBulkAddTransactions: (
    txs: Array<Omit<Transaction, "id" | "createdAt">>
  ) => void;
  onAddTransaction: (tx: Omit<Transaction, "id" | "createdAt">) => void;
}

const SAMPLE_CSV_PREVIEW: Array<Omit<Transaction, "id" | "createdAt">> = [
  {
    date: "08-10-2026",
    isoDate: "2026-10-08",
    merchant: "Zepto",
    amount: 340,
    category: "Food",
    description: "Milk, bread & hostel snacks",
    source: "CSV",
  },
  {
    date: "08-10-2026",
    isoDate: "2026-10-08",
    merchant: "Ola Cabs",
    amount: 210,
    category: "Transport",
    description: "Railway station drop",
    source: "CSV",
  },
  {
    date: "08-10-2026",
    isoDate: "2026-10-08",
    merchant: "Udemy",
    amount: 499,
    category: "Education",
    description: "LangGraph & Agentic AI course",
    source: "CSV",
  },
];

export const UploadPage: React.FC<UploadPageProps> = ({
  onBulkAddTransactions,
  onAddTransaction,
}) => {
  // Section A: CSV Upload State
  const [csvRows, setCsvRows] = useState<
    Array<Omit<Transaction, "id" | "createdAt">>
  >([]);
  const [csvFilename, setCsvFilename] = useState<string>("");
  const [csvStatus, setCsvStatus] = useState<string | null>(null);

  // Section B: Receipt OCR State
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractedReceipt, setExtractedReceipt] =
    useState<ExtractedReceipt | null>(null);
  const [ocrSavedMsg, setOcrSavedMsg] = useState<string | null>(null);

  // Editable receipt fields post-OCR
  const [editMerchant, setEditMerchant] = useState<string>("");
  const [editDate, setEditDate] = useState<string>("");
  const [editTax, setEditTax] = useState<string>("");
  const [editTotal, setEditTotal] = useState<string>("");
  const [editCategory, setEditCategory] = useState<CategoryName>("Food");
  const [editItemsText, setEditItemsText] = useState<string>("");

  const handleCsvFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvFilename(file.name);
    setCsvStatus(null);

    const reader = new FileReader();
    reader.onload = (evt) => {
      const content = String(evt.target?.result || "");
      const lines = content
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter(Boolean);
      if (lines.length < 2) {
        setCsvStatus("CSV file must contain a header row and at least one data row.");
        return;
      }

      const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
      const dateIdx = headers.indexOf("date");
      const merchantIdx = headers.indexOf("merchant");
      const amountIdx = headers.indexOf("amount");
      const catIdx = headers.indexOf("category");
      const descIdx = headers.indexOf("description");

      const parsed: Array<Omit<Transaction, "id" | "createdAt">> = [];
      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(",").map((c) => c.trim());
        if (cols.length < 3) continue;
        const rawDate = dateIdx >= 0 ? cols[dateIdx] : "08-10-2026";
        const merchant = merchantIdx >= 0 ? cols[merchantIdx] : cols[1];
        const amount = parseFloat(amountIdx >= 0 ? cols[amountIdx] : cols[2]) || 0;
        const description = descIdx >= 0 ? cols[descIdx] : "CSV Statement Import";
        const rawCat = catIdx >= 0 ? cols[catIdx] : "";
        const category: CategoryName = CATEGORIES.includes(rawCat as CategoryName)
          ? (rawCat as CategoryName)
          : categorizeExpense(merchant, description);

        const { display, iso } = normalizeToDisplayDate(rawDate);
        if (amount > 0) {
          parsed.push({
            date: display,
            isoDate: iso,
            merchant,
            amount,
            category,
            description,
            source: "CSV",
          });
        }
      }
      setCsvRows(parsed);
    };
    reader.readAsText(file);
  };

  const handleLoadSampleCsv = () => {
    setCsvFilename("data/sample_transactions.csv (3 new rows)");
    setCsvRows(SAMPLE_CSV_PREVIEW);
    setCsvStatus(null);
  };

  const handleImportCsvRows = () => {
    if (csvRows.length === 0) return;
    onBulkAddTransactions(csvRows);
    setCsvStatus(
      `Imported ${csvRows.length} transactions into SQLite via tools/database_tool.py!`
    );
    setCsvRows([]);
  };

  const populateReceiptEditor = (data: ExtractedReceipt) => {
    setExtractedReceipt(data);
    setEditMerchant(data.merchant);
    setEditDate(data.date);
    setEditTax(String(data.tax));
    setEditTotal(String(data.total));
    setEditCategory(
      CATEGORIES.includes(data.category) ? data.category : "Food"
    );
    setEditItemsText(
      data.items.map((i) => `${i.name} (₹${i.price})`).join(", ")
    );
    setOcrSavedMsg(null);
  };

  const handleReceiptImageUpload = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsExtracting(true);
    setOcrSavedMsg(null);

    try {
      const reader = new FileReader();
      reader.onload = async (evt) => {
        const dataUrl = String(evt.target?.result || "");
        const base64Part = dataUrl.includes(",")
          ? dataUrl.split(",")[1]
          : "";

        const response = await fetch("/api/ocr/extract", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            imageBase64: base64Part,
            mimeType: file.type,
            filename: file.name,
          }),
        });
        const result = await response.json();
        populateReceiptEditor(result);
        setIsExtracting(false);
      };
      reader.readAsDataURL(file);
    } catch {
      setIsExtracting(false);
    }
  };

  const handleTriggerDemoReceipt = async (presetFilename: string) => {
    setIsExtracting(true);
    setOcrSavedMsg(null);
    try {
      const response = await fetch("/api/ocr/extract", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: presetFilename }),
      });
      const result = await response.json();
      populateReceiptEditor(result);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleSaveReceiptToSqlite = (e: React.FormEvent) => {
    e.preventDefault();
    const totalVal = parseFloat(editTotal) || 0;
    if (!editMerchant.trim() || totalVal <= 0) return;

    const { display, iso } = normalizeToDisplayDate(editDate);
    onAddTransaction({
      date: display,
      isoDate: iso,
      merchant: editMerchant.trim(),
      amount: totalVal,
      category: editCategory,
      description: `${editItemsText} (Tax: ₹${editTax})`,
      source: "Receipt",
    });

    setOcrSavedMsg(
      `Stored Receipt Transaction (${editMerchant.trim()} — ${formatINR(
        totalVal
      )}) in SQLite under ${editCategory}!`
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-slate-200">
        <p className="text-xs font-medium text-teal-700">
          03. Multi-Modal Expense Ingestion · `pages/upload.py` &amp; `tools/ocr_tool.py`
        </p>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">
          Upload Expense (CSV &amp; Receipt OCR)
        </h1>
        <p className="text-sm text-slate-600 mt-0.5">
          Batch-import CSV transaction statements or extract structured receipt
          fields via OCR and auto-categorize into SQLite.
        </p>
      </div>

      {/* Pipeline Visual Diagram */}
      <div className="bg-slate-900 text-white rounded-xl p-5">
        <div className="text-xs font-medium text-teal-400 mb-2">
          Receipt Extraction &amp; Categorization Pipeline (`tools/ocr_tool.py`)
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          <span className="px-3 py-1.5 rounded bg-white/10">
            1. Receipt Image (JPG/PNG)
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
          <span className="px-3 py-1.5 rounded bg-white/10">
            2. OCR (`extract_receipt`)
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
          <span className="px-3 py-1.5 rounded bg-teal-500/20 text-teal-200 border border-teal-500/30">
            3. Extract: Merchant · Date · Items · Tax · Total
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
          <span className="px-3 py-1.5 rounded bg-white/10">
            4. Categorization (`categorize_expense`)
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
          <span className="px-3 py-1.5 rounded bg-emerald-500/20 text-emerald-200 border border-emerald-500/30">
            5. SQLite (`add_transaction`)
          </span>
        </div>
      </div>

      {/* Two Main Sections: A. Upload CSV | B. Upload Receipt */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SECTION A: UPLOAD CSV */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2.5">
                <div className="p-2.5 rounded-lg bg-slate-100 text-slate-800">
                  <FileSpreadsheet className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    A. Upload CSV Transactions
                  </h2>
                  <p className="text-xs text-slate-500">
                    Columns: `date, merchant, amount, category, description`
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleLoadSampleCsv}
                className="px-3 py-1.5 text-xs font-medium text-teal-700 bg-teal-50 hover:bg-teal-100 rounded-lg transition-colors whitespace-nowrap cursor-pointer"
              >
                Load Sample CSV
              </button>
            </div>

            <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 hover:border-teal-600 rounded-xl p-6 cursor-pointer bg-slate-50/50 transition-colors">
              <UploadCloud className="w-7 h-7 text-slate-400 mb-2" />
              <span className="text-xs font-semibold text-slate-700">
                Click to select a `.csv` transaction statement
              </span>
              <span className="text-xs text-slate-500 mt-0.5">
                Automatically categorizes rows missing a category column
              </span>
              <input
                type="file"
                accept=".csv"
                onChange={handleCsvFileUpload}
                className="hidden"
              />
            </label>

            {csvRows.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800">
                    Previewing {csvRows.length} rows from `{csvFilename}`
                  </span>
                  <span className="font-mono text-slate-600">
                    Total:{" "}
                    {formatINR(
                      csvRows.reduce((acc, r) => acc + r.amount, 0)
                    )}
                  </span>
                </div>

                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                      <tr>
                        <th className="py-2 px-3">Date</th>
                        <th className="py-2 px-3">Merchant</th>
                        <th className="py-2 px-3 text-right">Amount</th>
                        <th className="py-2 px-3">Auto-Category</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {csvRows.slice(0, 6).map((row, idx) => (
                        <tr key={idx}>
                          <td className="py-2 px-3 font-mono">{row.date}</td>
                          <td className="py-2 px-3 font-medium text-slate-900">
                            {row.merchant}
                          </td>
                          <td className="py-2 px-3 text-right font-mono">
                            {formatINR(row.amount)}
                          </td>
                          <td className="py-2 px-3 text-teal-700 font-medium">
                            {row.category}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <button
                  type="button"
                  onClick={handleImportCsvRows}
                  className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                >
                  Commit {csvRows.length} CSV Transactions to SQLite
                </button>
              </div>
            )}

            {csvStatus && (
              <div className="flex items-center gap-2 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{csvStatus}</span>
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-slate-100 text-xs text-slate-500">
            Team Member 3 Interface:{" "}
            <code className="font-mono text-slate-700">
              tools/database_tool.py :: bulk_insert_transactions(records)
            </code>
          </div>
        </div>

        {/* SECTION B: UPLOAD RECEIPT (OCR) */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2.5">
                <div className="p-2.5 rounded-lg bg-teal-50 text-teal-700">
                  <Receipt className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    B. Upload Receipt Image (OCR)
                  </h2>
                  <p className="text-xs text-slate-500">
                    Extracts Merchant, Date, Items, Tax, Total &amp; Category
                  </p>
                </div>
              </div>
            </div>

            {/* Preset sample receipts for quick demo testing */}
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-slate-600">
                Test OCR Extraction with a Sample Receipt or Upload Image:
              </span>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() =>
                    handleTriggerDemoReceipt("starbucks_receipt.jpg")
                  }
                  className="px-3 py-2 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg flex items-center justify-center gap-1.5 cursor-pointer whitespace-nowrap"
                >
                  <FileText className="w-3.5 h-3.5 text-teal-700" />
                  Starbucks (₹550)
                </button>
                <button
                  type="button"
                  onClick={() => handleTriggerDemoReceipt("amazon_shoes.png")}
                  className="px-3 py-2 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg flex items-center justify-center gap-1.5 cursor-pointer whitespace-nowrap"
                >
                  <FileText className="w-3.5 h-3.5 text-red-600" />
                  Amazon (₹1,800)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleTriggerDemoReceipt("apollo_pharmacy.jpg")
                  }
                  className="px-3 py-2 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg flex items-center justify-center gap-1.5 cursor-pointer whitespace-nowrap"
                >
                  <FileText className="w-3.5 h-3.5 text-emerald-700" />
                  Apollo (₹480)
                </button>
              </div>
            </div>

            <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 hover:border-teal-600 rounded-xl p-5 cursor-pointer bg-slate-50/50 transition-colors">
              <UploadCloud className="w-6 h-6 text-slate-400 mb-1.5" />
              <span className="text-xs font-semibold text-slate-700">
                Upload Receipt Image (`.jpg`, `.png`)
              </span>
              <span className="text-xs text-slate-500 mt-0.5">
                Calls `extract_receipt(image)` in `tools/ocr_tool.py`
              </span>
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg"
                onChange={handleReceiptImageUpload}
                className="hidden"
              />
            </label>

            {isExtracting && (
              <div className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg p-3 font-mono">
                Running OCR extraction pipeline...
              </div>
            )}

            {extractedReceipt && !isExtracting && (
              <form
                onSubmit={handleSaveReceiptToSqlite}
                className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3"
              >
                <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                  <span className="text-xs font-semibold text-slate-900">
                    Extracted Receipt Data
                  </span>
                  <span className="text-xs font-mono text-teal-700">
                    {extractedReceipt.engine}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Merchant
                    </label>
                    <input
                      type="text"
                      value={editMerchant}
                      onChange={(e) => setEditMerchant(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Date (DD-MM-YYYY)
                    </label>
                    <input
                      type="text"
                      value={editDate}
                      onChange={(e) => setEditDate(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-md font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Extracted Tax (₹)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={editTax}
                      onChange={(e) => setEditTax(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-md font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Total Amount (₹)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={editTotal}
                      onChange={(e) => setEditTotal(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-md font-mono font-semibold"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Extracted Line Items
                    </label>
                    <input
                      type="text"
                      value={editItemsText}
                      onChange={(e) => setEditItemsText(e.target.value)}
                      className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-md"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">
                      Auto-Assigned Category
                    </label>
                    <select
                      value={editCategory}
                      onChange={(e) =>
                        setEditCategory(e.target.value as CategoryName)
                      }
                      className="w-full px-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded-md"
                    >
                      {CATEGORIES.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <button
                  type="submit"
                  className="w-full py-2 bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold rounded-lg transition-colors cursor-pointer"
                >
                  Confirm &amp; Store Receipt in SQLite
                </button>
              </form>
            )}

            {ocrSavedMsg && (
              <div className="flex items-center gap-2 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{ocrSavedMsg}</span>
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-slate-100 text-xs text-slate-500">
            Team Member 2 Interface:{" "}
            <code className="font-mono text-slate-700">
              tools/ocr_tool.py :: extract_receipt(image) -&gt; dict
            </code>
          </div>
        </div>
      </div>
    </div>
  );
};
