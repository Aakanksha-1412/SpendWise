import React, { useEffect, useState } from "react";
import {
  FolderTree,
  Users,
  Copy,
  Check,
  Terminal,
  FileCode,
  GitBranch,
} from "lucide-react";
import { ProjectFileItem } from "../types/spendwise";

export const TeamArchitecturePage: React.FC = () => {
  const [files, setFiles] = useState<ProjectFileItem[]>([]);
  const [selectedPath, setSelectedPath] = useState<string>("SpendWise/app.py");
  const [copiedFile, setCopiedFile] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetch("/api/project-files")
      .then((res) => res.json())
      .then((data) => {
        if (data.files && Array.isArray(data.files)) {
          setFiles(data.files);
          const defaultFile =
            data.files.find((f: ProjectFileItem) => f.path === "SpendWise/app.py") ||
            data.files[0];
          if (defaultFile) setSelectedPath(defaultFile.path);
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const activeFile = files.find((f) => f.path === selectedPath) || files[0];

  const handleCopyCode = (content: string, path: string) => {
    navigator.clipboard.writeText(content);
    setCopiedFile(path);
    setTimeout(() => setCopiedFile(null), 2000);
  };

  const teamModules = [
    {
      member: "Team Member 1: Agent & LangGraph Orchestration",
      files: ["agent/graph.py", "agent/state.py", "agent/prompts.py"],
      interfaces: "run_agent(user_query, uploaded_receipt=None) -> dict",
      integration:
        "Integrates LangGraph StateGraph, Gemini/OpenAI LLM tool-calling, and ChromaDB semantic memory.",
    },
    {
      member: "Team Member 2: OCR & Receipt Extraction",
      files: ["tools/ocr_tool.py", "tools/categorization_tool.py"],
      interfaces:
        "extract_receipt(image) -> dict | categorize_expense(merchant, desc) -> str",
      integration:
        "Integrates pytesseract (Tesseract OCR) or Vision LLM API to extract Merchant, Date, Items, Tax, and Total.",
    },
    {
      member: "Team Member 3: SQLite Database & Transactions",
      files: ["database/database.py", "tools/database_tool.py"],
      interfaces:
        "add_transaction(tx) | get_transactions() | get_category_spending(category)",
      integration:
        "Manages SQLite3 schema (`transactions` & `budgets` tables), bulk CSV imports, and parameterized queries.",
    },
    {
      member: "Team Member 4: Pandas Analytics, Budget & Spike Detector",
      files: [
        "analytics/analytics.py",
        "tools/budget_tool.py",
        "tools/spike_detector.py",
      ],
      interfaces:
        "calculate_budget_status(category) | detect_spending_spike(category)",
      integration:
        "Executes all Pandas DataFrame aggregations, budget overrun checks, and weekly spending spike detection.",
    },
    {
      member: "UI / Integration Team: Multi-Page Streamlit Dashboard",
      files: [
        "app.py",
        "pages/home.py",
        "pages/transactions.py",
        "pages/upload.py",
        "pages/budget.py",
        "pages/analytics.py",
        "pages/assistant.py",
      ],
      interfaces: "st.navigation() & st.switch_page() across all 6 pages",
      integration:
        "Renders Plotly charts, interactive filters, and forms while delegating all logic to `tools/` and `analytics/`.",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-slate-200">
        <p className="text-xs font-medium text-teal-700">
          07. Python + Streamlit + LangGraph Codebase Explorer &amp; Team Guide
        </p>
        <h1 className="text-2xl font-bold text-slate-900 mt-1">
          Python Project Files &amp; Team Collaboration Architecture
        </h1>
        <p className="text-sm text-slate-600 mt-0.5">
          Inspect and copy all generated Python 3.10+ Streamlit, LangGraph,
          SQLite3, and Pandas files located in the{" "}
          <code className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded">
            /SpendWise
          </code>{" "}
          directory.
        </p>
      </div>

      {/* Quick Terminal Commands */}
      <div className="bg-slate-900 text-slate-100 rounded-xl p-5 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-teal-400">
            <Terminal className="w-4 h-4" />
            <span>1. Installation &amp; Environment Setup</span>
          </div>
          <pre className="text-xs font-mono bg-black/40 p-3.5 rounded-lg overflow-x-auto text-slate-200 leading-relaxed">
{`cd SpendWise
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env`}
          </pre>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
            <GitBranch className="w-4 h-4" />
            <span>2. Run the Multi-Page Streamlit Application</span>
          </div>
          <pre className="text-xs font-mono bg-black/40 p-3.5 rounded-lg overflow-x-auto text-slate-200 leading-relaxed">
{`# Starts the Streamlit server with SQLite auto-seeding
streamlit run app.py

# Opens at http://localhost:8501`}
          </pre>
        </div>
      </div>

      {/* Team Collaboration Matrix (WHO WORKS WHERE) */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-teal-700" />
          <h2 className="text-base font-semibold text-slate-900">
            Team Collaboration Matrix — Who Works Where (Zero Merge Conflicts)
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold">
                <th className="py-3 px-4">Team Role</th>
                <th className="py-3 px-4">Owned Files</th>
                <th className="py-3 px-4">Exposed Function Contracts</th>
                <th className="py-3 px-4">Integration Responsibility</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {teamModules.map((tm) => (
                <tr key={tm.member} className="hover:bg-slate-50/70">
                  <td className="py-3 px-4 font-semibold text-slate-900">
                    {tm.member}
                  </td>
                  <td className="py-3 px-4 font-mono text-teal-800">
                    {tm.files.join(", ")}
                  </td>
                  <td className="py-3 px-4 font-mono text-slate-700">
                    {tm.interfaces}
                  </td>
                  <td className="py-3 px-4 text-slate-600">{tm.integration}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Interactive Python File Viewer */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 min-h-[560px]">
        {/* Left File Tree */}
        <div className="lg:col-span-4 border-b lg:border-b-0 lg:border-r border-slate-200 bg-slate-50/60 p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-800 px-2">
            <FolderTree className="w-4 h-4 text-teal-700" />
            <span>SpendWise/ Directory ({files.length} files)</span>
          </div>

          {loading ? (
            <div className="p-4 text-xs text-slate-500 font-mono">
              Loading Python project files...
            </div>
          ) : (
            <div className="space-y-1 max-h-[520px] overflow-y-auto pr-1">
              {files.map((file) => {
                const isSelected = file.path === selectedPath;
                return (
                  <button
                    key={file.path}
                    type="button"
                    onClick={() => setSelectedPath(file.path)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors flex items-center justify-between gap-2 cursor-pointer ${
                      isSelected
                        ? "bg-slate-900 text-white font-semibold"
                        : "text-slate-700 hover:bg-slate-200/70"
                    }`}
                  >
                    <span className="font-mono truncate">{file.path}</span>
                    <FileCode
                      className={`w-3.5 h-3.5 shrink-0 ${
                        isSelected ? "text-teal-400" : "text-slate-400"
                      }`}
                    />
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Code Viewer */}
        <div className="lg:col-span-8 flex flex-col">
          {activeFile ? (
            <>
              <div className="px-5 py-3.5 border-b border-slate-200 bg-white flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <div className="text-sm font-bold font-mono text-slate-900">
                    {activeFile.path}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    <strong>Owner:</strong> {activeFile.owner} ·{" "}
                    {activeFile.moduleRole}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    handleCopyCode(activeFile.content, activeFile.path)
                  }
                  className="px-3 py-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg flex items-center gap-1.5 self-start cursor-pointer whitespace-nowrap"
                >
                  {copiedFile === activeFile.path ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      Copy File Code
                    </>
                  )}
                </button>
              </div>

              <pre className="flex-1 p-5 bg-slate-950 text-slate-100 font-mono text-xs leading-relaxed overflow-auto max-h-[520px]">
                <code>{activeFile.content}</code>
              </pre>
            </>
          ) : (
            <div className="p-8 text-sm text-slate-500">
              Select a file from the left tree to view its code.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
