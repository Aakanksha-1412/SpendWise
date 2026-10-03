import express from "express";
import { createServer as createViteServer } from "vite";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import dotenv from "dotenv";
import { GoogleGenAI, Type } from "@google/genai";

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;

app.use(express.json({ limit: "15mb" }));

// Helper to initialize Gemini client on server side when GEMINI_API_KEY is available
function getGeminiClient(): GoogleGenAI | null {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || apiKey === "MY_GEMINI_API_KEY" || apiKey.trim() === "") {
    return null;
  }
  return new GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        "User-Agent": "aistudio-build",
      },
    },
  });
}

// Metadata mapping for the SpendWise Python files to help team members see ownership
const FILE_METADATA: Record<
  string,
  { owner: string; moduleRole: string }
> = {
  "app.py": {
    owner: "UI / Frontend Team",
    moduleRole: "Main Streamlit entry point, page config, and multipage navigation router",
  },
  "pages/home.py": {
    owner: "UI / Frontend Team",
    moduleRole: "Executive financial dashboard, KPI cards, quick navigation, Plotly Budget vs Actual chart, and AI insights",
  },
  "pages/transactions.py": {
    owner: "UI / Frontend Team",
    moduleRole: "Filterable transaction ledger (Category, Date, Merchant) + Natural Language & form expense entry",
  },
  "pages/upload.py": {
    owner: "UI / Team Member 2",
    moduleRole: "CSV batch transaction uploader and Receipt OCR extraction pipeline UI",
  },
  "pages/budget.py": {
    owner: "UI / Team Member 4",
    moduleRole: "Monthly category budget configuration and utilization status monitor",
  },
  "pages/analytics.py": {
    owner: "UI / Team Member 4",
    moduleRole: "6 Plotly analytics views (Category, Budget vs Actual, Weekly, Monthly, Trends, Spike Detection)",
  },
  "pages/assistant.py": {
    owner: "UI / Team Member 1",
    moduleRole: "Ask SpendWise conversational UI with LangGraph tool routing trace viewer",
  },
  "agent/graph.py": {
    owner: "Team Member 1 (Agent / LangGraph)",
    moduleRole: "5-node LangGraph StateGraph: Understand -> Decide Tool -> Call Tool -> Evaluate -> Generate Response",
  },
  "agent/state.py": {
    owner: "Team Member 1 (Agent / LangGraph)",
    moduleRole: "TypedDict AgentState definition shared across LangGraph nodes",
  },
  "agent/prompts.py": {
    owner: "Team Member 1 (Agent / LangGraph)",
    moduleRole: "System prompts for intent classification, tool routing, and financial response generation",
  },
  "tools/ocr_tool.py": {
    owner: "Team Member 2 (OCR / Receipt Extraction)",
    moduleRole: "Receipt image extraction interface: extract_receipt(image) -> Merchant, Date, Items, Tax, Total",
  },
  "tools/database_tool.py": {
    owner: "Team Member 3 (Database + Transactions)",
    moduleRole: "SQLite CRUD & query functions: add_transaction, get_transactions, get_category_spending, upsert_budget",
  },
  "tools/categorization_tool.py": {
    owner: "Team Member 1 & 2 (Categorization / ChromaDB)",
    moduleRole: "Automatic expense categorization and natural-language expense parser",
  },
  "tools/budget_tool.py": {
    owner: "Team Member 4 (Analytics + Budget + Spikes)",
    moduleRole: "Budget vs Actual calculation and discretionary spending reallocation advisor",
  },
  "tools/spike_detector.py": {
    owner: "Team Member 4 (Analytics + Budget + Spikes)",
    moduleRole: "Weekly spending anomaly & spike detector: detect_spending_spike(category)",
  },
  "database/database.py": {
    owner: "Team Member 3 (Database + Transactions)",
    moduleRole: "SQLite3 connection factory, schema creation (transactions & budgets tables), and initial demo seeding",
  },
  "analytics/analytics.py": {
    owner: "Team Member 4 (Analytics + Budget + Spikes)",
    moduleRole: "Pandas DataFrame aggregations for KPIs, weekly/monthly comparisons, and daily trends",
  },
  "utils/helpers.py": {
    owner: "Shared / All Team Members",
    moduleRole: "Official 8 categories, INR currency formatting, and date normalization utilities",
  },
  "data/sample_transactions.csv": {
    owner: "Shared / Test Dataset",
    moduleRole: "Sample CSV transactions dataset for testing batch upload and categorization",
  },
  "requirements.txt": {
    owner: "Shared / DevOps",
    moduleRole: "Python 3.10+ dependencies: streamlit, langgraph, langchain, pandas, plotly, chromadb, pytesseract",
  },
  ".env.example": {
    owner: "Shared / Security",
    moduleRole: "Environment variable template for GEMINI_API_KEY, SPENDWISE_DB_PATH, and CHROMA_PERSIST_DIR",
  },
  ".gitignore": {
    owner: "Shared / Git Workflow",
    moduleRole: "Excludes .env, __pycache__, virtual environments, and local SQLite/ChromaDB binaries",
  },
  "README.md": {
    owner: "Shared / Documentation",
    moduleRole: "Complete project architecture, setup instructions, and team collaboration guide",
  },
};

// Recursively read files in /SpendWise
function readSpendWiseDirectory(dirPath: string, baseDir: string): Array<{
  path: string;
  owner: string;
  moduleRole: string;
  content: string;
}> {
  const results: Array<{
    path: string;
    owner: string;
    moduleRole: string;
    content: string;
  }> = [];

  if (!fs.existsSync(dirPath)) return results;

  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);
    const relPath = path.relative(baseDir, fullPath).replace(/\\/g, "/");

    if (entry.isDirectory()) {
      if (entry.name === "__pycache__" || entry.name === "assets") continue;
      results.push(...readSpendWiseDirectory(fullPath, baseDir));
    } else {
      if (entry.name.endsWith(".db") || entry.name === "__init__.py") continue;
      const content = fs.readFileSync(fullPath, "utf-8");
      const meta = FILE_METADATA[relPath] || {
        owner: "SpendWise Team",
        moduleRole: "Project module file",
      };
      results.push({
        path: `SpendWise/${relPath}`,
        owner: meta.owner,
        moduleRole: meta.moduleRole,
        content,
      });
    }
  }
  return results;
}

// API: Get all SpendWise Python project files
app.get("/api/project-files", (_req, res) => {
  try {
    const spendwiseRoot = path.join(__dirname, "SpendWise");
    const files = readSpendWiseDirectory(spendwiseRoot, spendwiseRoot);
    res.json({ files });
  } catch (err: any) {
    res.status(500).json({ error: err?.message || "Failed to read project files" });
  }
});

// API: Vision OCR Receipt Extraction using server-side Gemini (with deterministic fallback)
app.post("/api/ocr/extract", async (req, res) => {
  const { imageBase64, mimeType, filename } = req.body || {};
  const ai = getGeminiClient();

  if (ai && imageBase64) {
    try {
      const response = await ai.models.generateContent({
        model: "gemini-3.8-flash",
        contents: {
          parts: [
            {
              inlineData: {
                data: imageBase64,
                mimeType: mimeType || "image/jpeg",
              },
            },
            {
              text: "Extract the receipt details into JSON. Category must be one of: Food, Transport, Shopping, Entertainment, Bills, Healthcare, Education, Others. Date should be DD-MM-YYYY.",
            },
          ],
        },
        config: {
          responseMimeType: "application/json",
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              merchant: { type: Type.STRING },
              date: { type: Type.STRING },
              items: {
                type: Type.ARRAY,
                items: {
                  type: Type.OBJECT,
                  properties: {
                    name: { type: Type.STRING },
                    price: { type: Type.NUMBER },
                  },
                },
              },
              tax: { type: Type.NUMBER },
              total: { type: Type.NUMBER },
              category: { type: Type.STRING },
            },
            required: ["merchant", "date", "items", "tax", "total", "category"],
          },
        },
      });

      const parsed = JSON.parse(response.text?.trim() || "{}");
      return res.json({
        ...parsed,
        engine: "Vision LLM OCR (gemini-3.8-flash)",
      });
    } catch (error) {
      // Fall through to deterministic OCR simulation if API call fails
    }
  }

  // Deterministic OCR extraction matching tools/ocr_tool.py
  const lowerName = (filename || "starbucks_receipt.jpg").toLowerCase();
  if (lowerName.includes("amazon") || lowerName.includes("shoe") || lowerName.includes("shop")) {
    return res.json({
      merchant: "Amazon Retail India",
      date: "02-10-2026",
      items: [{ name: "Running Shoes (Size 9)", price: 1525.42 }],
      tax: 274.58,
      total: 1800.0,
      category: "Shopping",
      engine: "tools/ocr_tool.py (Demo OCR Pipeline — Ready for Tesseract / Vision LLM)",
    });
  }
  if (lowerName.includes("apollo") || lowerName.includes("pharm") || lowerName.includes("med")) {
    return res.json({
      merchant: "Apollo Pharmacy",
      date: "06-10-2026",
      items: [
        { name: "Multivitamin Tablets (30s)", price: 310.0 },
        { name: "First Aid Antiseptic Kit", price: 118.57 },
      ],
      tax: 51.43,
      total: 480.0,
      category: "Healthcare",
      engine: "tools/ocr_tool.py (Demo OCR Pipeline — Ready for Tesseract / Vision LLM)",
    });
  }

  return res.json({
    merchant: "Starbucks Coffee",
    date: "08-10-2026",
    items: [
      { name: "Java Chip Frappuccino (Tall)", price: 315.0 },
      { name: "Smoked Chicken Panini", price: 208.8 },
    ],
    tax: 26.2,
    total: 550.0,
    category: "Food",
    engine: "tools/ocr_tool.py (Demo OCR Pipeline — Ready for Tesseract / Vision LLM)",
  });
});

// API: Agentic Orchestration Response Synthesis via Gemini (optional enhancement over deterministic tool output)
app.post("/api/agent/synthesize", async (req, res) => {
  const { userQuery, intent, selectedTools, toolOutputs, fallbackResponse } = req.body || {};
  const ai = getGeminiClient();

  if (!ai) {
    return res.json({
      response: fallbackResponse,
      mode: "Deterministic LangGraph State Pipeline (Offline Demo Mode)",
    });
  }

  try {
    const response = await ai.models.generateContent({
      model: "gemini-3.8-flash",
      contents: `User Request: "${userQuery}"
Detected Intent: ${intent}
Executed SpendWise Tools: ${JSON.stringify(selectedTools)}
Deterministic Tool Outputs (SQLite + Pandas):
${JSON.stringify(toolOutputs, null, 2)}

Write a clear, concise, helpful financial assistant response in Markdown based strictly on the exact numeric values in the Deterministic Tool Outputs above. Use Indian Rupees (₹). Highlight any budget alerts, remaining balances, or discretionary spending recommendations.`,
      config: {
        systemInstruction:
          "You are SpendWise, an autonomous personal financial expense and budgeting assistant. Never invent numbers; strictly report the exact figures returned by the Python/Pandas tools.",
      },
    });

    return res.json({
      response: response.text || fallbackResponse,
      mode: "LangGraph + Gemini 3.8 Flash Orchestrator",
    });
  } catch (err) {
    return res.json({
      response: fallbackResponse,
      mode: "Deterministic LangGraph State Pipeline",
    });
  }
});

async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(__dirname, "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`SpendWise Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
