import React, { useState } from "react";
import {
  Bot,
  Send,
  ChevronDown,
  ChevronRight,
  Cpu,
  User,
  ArrowRight,
} from "lucide-react";
import {
  CategoryName,
  ChatMessage,
  Transaction,
} from "../types/spendwise";
import { executeLocalAgentGraph } from "../services/spendwiseEngine";

interface AssistantPageProps {
  transactions: Transaction[];
  budgets: Record<CategoryName, number>;
  onAddTransaction: (tx: Omit<Transaction, "id" | "createdAt">) => Transaction;
}

const EXAMPLE_QUESTIONS: string[] = [
  "How much did I spend on food this month?",
  "How much of my food budget is left?",
  "Why did I receive a shopping alert?",
  "Which category increased the most?",
  "Can I afford another ₹500 expense in food?",
  "Show me where I can reduce my spending.",
  "Add this restaurant receipt of ₹550 at Starbucks and tell me how much of my food budget is left.",
];

export const AssistantPage: React.FC<AssistantPageProps> = ({
  transactions,
  budgets,
  onAddTransaction,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-msg",
      role: "assistant",
      content:
        "Hello! I am **SpendWise**, your autonomous personal financial orchestrator (`agent/graph.py`).\n\nUnlike a basic chatbot, I route every request through a **5-stage LangGraph pipeline**:\n1. **Understand Request** (`understand_request_node`)\n2. **Decide Required Tool(s)** (`decide_required_tool_node`)\n3. **Call Deterministic Tool(s)** (`ocr_tool`, `database_tool`, `categorization_tool`, `budget_tool`, `spike_detector`)\n4. **Evaluate Result** (`evaluate_result_node`)\n5. **Generate Response** (`generate_response_node`)\n\nSelect any question below or type your own financial request!",
      timestamp: "Just now",
      intent: "SYSTEM_READY",
      selectedTools: [
        "ocr_tool.py",
        "database_tool.py",
        "categorization_tool.py",
        "budget_tool.py",
        "spike_detector.py",
      ],
    },
  ]);

  const [inputQuery, setInputQuery] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [expandedTraces, setExpandedTraces] = useState<Record<string, boolean>>({
    "welcome-msg": false,
  });

  const toggleTrace = (id: string) => {
    setExpandedTraces((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSendQuery = async (queryText: string) => {
    const trimmed = queryText.trim();
    if (!trimmed || isProcessing) return;

    const userMsgId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputQuery("");
    setIsProcessing(true);

    // 1. Execute the deterministic 5-node LangGraph pipeline locally first
    const graphResult = executeLocalAgentGraph(
      trimmed,
      transactions,
      budgets,
      onAddTransaction
    );

    let finalMarkdown = graphResult.fallbackResponse;
    let engineMode = "LangGraph Deterministic State Machine (`agent/graph.py`)";

    // 2. Optionally synthesize conversational response via server-side Gemini if configured
    try {
      const res = await fetch("/api/agent/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userQuery: trimmed,
          intent: graphResult.intent,
          selectedTools: graphResult.selectedTools,
          toolOutputs: graphResult.toolOutputs,
          fallbackResponse: graphResult.fallbackResponse,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.response) finalMarkdown = data.response;
        if (data.mode) engineMode = data.mode;
      }
    } catch {
      // Fallback response already prepared
    }

    const botMsgId = `bot-${Date.now()}`;
    const botMsg: ChatMessage = {
      id: botMsgId,
      role: "assistant",
      content: finalMarkdown,
      timestamp: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      intent: graphResult.intent,
      selectedTools: graphResult.selectedTools,
      trace: graphResult.trace,
      engineMode,
    };

    setMessages((prev) => [...prev, botMsg]);
    setExpandedTraces((prev) => ({ ...prev, [botMsgId]: true }));
    setIsProcessing(false);
  };

  const renderFormattedContent = (text: string) => {
    const lines = text.split("\n");
    return lines.map((line, idx) => {
      if (line.startsWith("### ")) {
        return (
          <h4 key={idx} className="font-bold text-slate-900 text-sm mt-2 mb-1">
            {line.replace("### ", "")}
          </h4>
        );
      }
      // Bold formatting
      const parts = line.split(/(\*\*.*?\*\*)/g);
      return (
        <p key={idx} className="leading-relaxed min-h-[0.75rem]">
          {parts.map((part, pIdx) => {
            if (part.startsWith("**") && part.endsWith("**")) {
              return (
                <strong key={pIdx} className="font-semibold text-slate-900">
                  {part.slice(2, -2)}
                </strong>
              );
            }
            return <span key={pIdx}>{part}</span>;
          })}
        </p>
      );
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-slate-200 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium text-teal-700">
            06. LangGraph Central Controller · `pages/assistant.py` &amp; `agent/graph.py`
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">
            🤖 Ask SpendWise
          </h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Agentic AI Orchestrator that separates LLM intent routing from
            deterministic Python/Pandas financial math.
          </p>
        </div>

        {/* Visual LangGraph Flow Diagram */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs font-mono bg-slate-900 text-white px-3.5 py-2 rounded-lg">
          <span className="text-teal-400">START</span>
          <ArrowRight className="w-3 h-3 text-slate-400" />
          <span>Understand</span>
          <ArrowRight className="w-3 h-3 text-slate-400" />
          <span>Decide Tool</span>
          <ArrowRight className="w-3 h-3 text-slate-400" />
          <span className="text-amber-300">Call Tool</span>
          <ArrowRight className="w-3 h-3 text-slate-400" />
          <span>Evaluate</span>
          <ArrowRight className="w-3 h-3 text-slate-400" />
          <span className="text-emerald-400">Respond</span>
        </div>
      </div>

      {/* Clickable Example Prompts */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-800">
            Click an example question to trigger the LangGraph Agent:
          </span>
          <span className="text-xs text-slate-500">
            Team Member 1 · `agent/graph.py`
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => handleSendQuery(q)}
              disabled={isProcessing}
              className="px-3 py-1.5 text-xs font-medium bg-slate-100 hover:bg-teal-50 hover:text-teal-800 border border-slate-200 hover:border-teal-300 rounded-lg text-slate-700 transition-colors cursor-pointer text-left"
            >
              “{q}”
            </button>
          ))}
        </div>
      </div>

      {/* Chat Conversation Stream */}
      <div className="bg-white border border-slate-200 rounded-xl flex flex-col min-h-[460px]">
        <div className="flex-1 p-6 space-y-5 overflow-y-auto max-h-[540px]">
          {messages.map((msg) => {
            const isUser = msg.role === "user";
            const isExpanded = !!expandedTraces[msg.id];

            return (
              <div
                key={msg.id}
                className={`flex items-start gap-3.5 ${
                  isUser ? "justify-end" : "justify-start"
                }`}
              >
                {!isUser && (
                  <div className="p-2.5 rounded-xl bg-slate-900 text-white shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-3xl rounded-xl p-4 space-y-3 ${
                    isUser
                      ? "bg-slate-900 text-white"
                      : "bg-slate-50 border border-slate-200 text-slate-800"
                  }`}
                >
                  <div className="flex items-center justify-between gap-4 text-xs opacity-75">
                    <span className="font-semibold">
                      {isUser ? "You" : "SpendWise Agent"}
                    </span>
                    <span className="font-mono">{msg.timestamp}</span>
                  </div>

                  <div className="text-sm space-y-1">
                    {isUser
                      ? msg.content
                      : renderFormattedContent(msg.content)}
                  </div>

                  {/* LangGraph Orchestration Trace Accordion */}
                  {!isUser && msg.trace && msg.trace.length > 0 && (
                    <div className="pt-2 border-t border-slate-200/80">
                      <button
                        type="button"
                        onClick={() => toggleTrace(msg.id)}
                        className="flex items-center justify-between w-full text-xs font-mono text-teal-800 bg-teal-50/90 hover:bg-teal-100/80 px-3 py-2 rounded-lg transition-colors cursor-pointer"
                      >
                        <span className="flex items-center gap-2 font-semibold">
                          <Cpu className="w-3.5 h-3.5 text-teal-700" />
                          LangGraph Execution Trace (Intent: {msg.intent})
                        </span>
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </button>

                      {isExpanded && (
                        <div className="mt-2 p-3 bg-slate-900 text-slate-200 rounded-lg space-y-2 text-xs font-mono">
                          {msg.trace.map((step, sIdx) => (
                            <div
                              key={sIdx}
                              className="border-l-2 border-teal-500 pl-2.5 py-0.5"
                            >
                              <div className="text-teal-300 font-semibold">
                                {step.node}{" "}
                                <span className="text-slate-400 font-normal">
                                  ({step.pythonModule})
                                </span>
                              </div>
                              <div className="text-slate-300 mt-0.5">
                                {step.detail}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {isUser && (
                  <div className="p-2.5 rounded-xl bg-teal-700 text-white shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {isProcessing && (
            <div className="flex items-center gap-3 text-xs font-mono text-slate-500 pl-2">
              <Cpu className="w-4 h-4 text-teal-700 animate-spin" />
              <span>
                LangGraph routing request → calling deterministic SQLite &amp;
                Pandas tools...
              </span>
            </div>
          )}
        </div>

        {/* Input Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendQuery(inputQuery);
          }}
          className="p-4 border-t border-slate-200 bg-slate-50/50 flex gap-3"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder='Ask SpendWise: "Add this restaurant receipt of ₹550 at Starbucks and tell me how much of my food budget is left."'
            className="flex-1 px-4 py-2.5 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:border-teal-700"
          />
          <button
            type="submit"
            disabled={isProcessing || !inputQuery.trim()}
            className="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-semibold rounded-lg flex items-center gap-2 transition-colors cursor-pointer whitespace-nowrap"
          >
            <Send className="w-3.5 h-3.5" />
            Send to Agent
          </button>
        </form>
      </div>
    </div>
  );
};
