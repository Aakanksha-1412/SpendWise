export type CategoryName =
  | "Food"
  | "Transport"
  | "Shopping"
  | "Entertainment"
  | "Bills"
  | "Healthcare"
  | "Education"
  | "Others";

export type ExpenseSource = "Text" | "CSV" | "Receipt";

export type PageId =
  | "home"
  | "transactions"
  | "upload"
  | "budget"
  | "analytics"
  | "assistant"
  | "architecture";

export interface Transaction {
  id: number;
  date: string; // DD-MM-YYYY
  isoDate: string; // YYYY-MM-DD for sorting/filtering
  merchant: string;
  amount: number;
  category: CategoryName;
  description: string;
  source: ExpenseSource;
  createdAt: string;
}

export interface CategoryBudgetStatus {
  category: CategoryName;
  budget: number;
  spent: number;
  remaining: number;
  utilizationPct: number;
  status: "UNDER BUDGET" | "NEAR LIMIT" | "OVER BUDGET";
}

export interface SpendingSpike {
  category: CategoryName;
  previousWeeklySpending: number;
  currentWeeklySpending: number;
  increaseAmount: number;
  increasePct: number;
  spikeDetected: boolean;
  message: string;
}

export interface ReceiptItem {
  name: string;
  price: number;
}

export interface ExtractedReceipt {
  merchant: string;
  date: string;
  items: ReceiptItem[];
  tax: number;
  total: number;
  category: CategoryName;
  engine: string;
}

export interface AgentTraceStep {
  node: string;
  pythonModule: string;
  detail: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  intent?: string;
  selectedTools?: string[];
  trace?: AgentTraceStep[];
  engineMode?: string;
}

export interface ProjectFileItem {
  path: string;
  owner: string;
  moduleRole: string;
  content: string;
}
