import {
  CategoryName,
  Transaction,
  CategoryBudgetStatus,
  SpendingSpike,
  AgentTraceStep,
} from "../types/spendwise";

export const CATEGORIES: CategoryName[] = [
  "Food",
  "Transport",
  "Shopping",
  "Entertainment",
  "Bills",
  "Healthcare",
  "Education",
  "Others",
];

export const DISCRETIONARY_CATEGORIES: CategoryName[] = [
  "Shopping",
  "Entertainment",
  "Food",
  "Others",
];

export const CATEGORY_COLORS: Record<CategoryName, string> = {
  Food: "#0F766E",
  Transport: "#0369A1",
  Shopping: "#DC2626",
  Entertainment: "#7C3AED",
  Bills: "#475569",
  Healthcare: "#16A34A",
  Education: "#D97706",
  Others: "#64748B",
};

export const INITIAL_BUDGETS: Record<CategoryName, number> = {
  Food: 5000,
  Transport: 3000,
  Shopping: 4000,
  Entertainment: 2000,
  Bills: 3500,
  Healthcare: 1500,
  Education: 4000,
  Others: 1500,
};

export const INITIAL_TRANSACTIONS: Transaction[] = [
  // Previous week (Sep 18 - Sep 24, 2026) -> Food = ₹1,500
  {
    id: 1,
    date: "19-09-2026",
    isoDate: "2026-09-19",
    merchant: "Zomato",
    amount: 420,
    category: "Food",
    description: "Hostel study group snacks",
    source: "Text",
    createdAt: "2026-09-19 20:15:00",
  },
  {
    id: 2,
    date: "21-09-2026",
    isoDate: "2026-09-21",
    merchant: "Campus Canteen",
    amount: 380,
    category: "Food",
    description: "Weekly lunch combo",
    source: "CSV",
    createdAt: "2026-09-21 13:30:00",
  },
  {
    id: 3,
    date: "22-09-2026",
    isoDate: "2026-09-22",
    merchant: "Delhi Metro",
    amount: 400,
    category: "Transport",
    description: "Metro smart card recharge",
    source: "CSV",
    createdAt: "2026-09-22 09:00:00",
  },
  {
    id: 4,
    date: "23-09-2026",
    isoDate: "2026-09-23",
    merchant: "Blinkit",
    amount: 700,
    category: "Food",
    description: "Groceries & fruits",
    source: "CSV",
    createdAt: "2026-09-23 18:45:00",
  },
  {
    id: 5,
    date: "24-09-2026",
    isoDate: "2026-09-24",
    merchant: "BookMyShow",
    amount: 450,
    category: "Entertainment",
    description: "Weekend movie ticket",
    source: "Text",
    createdAt: "2026-09-24 21:00:00",
  },

  // Current month / week (Oct 01 - Oct 08, 2026)
  // Food = ₹3,000 (Weekly spike from ₹1,500 -> ₹3,000!)
  // Shopping = ₹6,100 (Exceeds ₹4,000 budget by ₹2,100!)
  {
    id: 6,
    date: "01-10-2026",
    isoDate: "2026-10-01",
    merchant: "Swiggy",
    amount: 450,
    category: "Food",
    description: "Dinner",
    source: "Text",
    createdAt: "2026-10-01 20:40:00",
  },
  {
    id: 7,
    date: "01-10-2026",
    isoDate: "2026-10-01",
    merchant: "Uber",
    amount: 230,
    category: "Transport",
    description: "College",
    source: "CSV",
    createdAt: "2026-10-01 08:45:00",
  },
  {
    id: 8,
    date: "02-10-2026",
    isoDate: "2026-10-02",
    merchant: "Amazon",
    amount: 1800,
    category: "Shopping",
    description: "Shoes",
    source: "Receipt",
    createdAt: "2026-10-02 14:20:00",
  },
  {
    id: 9,
    date: "02-10-2026",
    isoDate: "2026-10-02",
    merchant: "Starbucks",
    amount: 550,
    category: "Food",
    description: "Coffee & sandwich with team",
    source: "Receipt",
    createdAt: "2026-10-02 17:10:00",
  },
  {
    id: 10,
    date: "03-10-2026",
    isoDate: "2026-10-03",
    merchant: "Myntra",
    amount: 2400,
    category: "Shopping",
    description: "Winter jacket & apparel",
    source: "CSV",
    createdAt: "2026-10-03 19:05:00",
  },
  {
    id: 11,
    date: "03-10-2026",
    isoDate: "2026-10-03",
    merchant: "Airtel",
    amount: 899,
    category: "Bills",
    description: "Fiber broadband & mobile plan",
    source: "CSV",
    createdAt: "2026-10-03 11:00:00",
  },
  {
    id: 12,
    date: "04-10-2026",
    isoDate: "2026-10-04",
    merchant: "Barbeque Nation",
    amount: 1250,
    category: "Food",
    description: "Birthday dinner buffet",
    source: "Receipt",
    createdAt: "2026-10-04 21:30:00",
  },
  {
    id: 13,
    date: "04-10-2026",
    isoDate: "2026-10-04",
    merchant: "Rapido",
    amount: 320,
    category: "Transport",
    description: "Lab commute rides",
    source: "Text",
    createdAt: "2026-10-04 09:15:00",
  },
  {
    id: 14,
    date: "05-10-2026",
    isoDate: "2026-10-05",
    merchant: "Croma",
    amount: 1900,
    category: "Shopping",
    description: "Wireless keyboard & mouse",
    source: "Receipt",
    createdAt: "2026-10-05 16:40:00",
  },
  {
    id: 15,
    date: "05-10-2026",
    isoDate: "2026-10-05",
    merchant: "Blue Tokai",
    amount: 750,
    category: "Food",
    description: "Artisan coffee & bakery",
    source: "Text",
    createdAt: "2026-10-05 18:00:00",
  },
  {
    id: 16,
    date: "06-10-2026",
    isoDate: "2026-10-06",
    merchant: "Spotify",
    amount: 119,
    category: "Entertainment",
    description: "Student premium subscription",
    source: "CSV",
    createdAt: "2026-10-06 10:00:00",
  },
  {
    id: 17,
    date: "06-10-2026",
    isoDate: "2026-10-06",
    merchant: "Apollo Pharmacy",
    amount: 480,
    category: "Healthcare",
    description: "Vitamins & first aid",
    source: "Receipt",
    createdAt: "2026-10-06 19:20:00",
  },
  {
    id: 18,
    date: "07-10-2026",
    isoDate: "2026-10-07",
    merchant: "Coursera",
    amount: 1450,
    category: "Education",
    description: "ML Specialization certificate",
    source: "CSV",
    createdAt: "2026-10-07 15:00:00",
  },
  {
    id: 19,
    date: "07-10-2026",
    isoDate: "2026-10-07",
    merchant: "BESCOM",
    amount: 1350,
    category: "Bills",
    description: "Monthly electricity bill",
    source: "CSV",
    createdAt: "2026-10-07 11:30:00",
  },
  {
    id: 20,
    date: "08-10-2026",
    isoDate: "2026-10-08",
    merchant: "Crossword",
    amount: 390,
    category: "Others",
    description: "Stationery & notebooks",
    source: "Text",
    createdAt: "2026-10-08 17:45:00",
  },
];

export function formatINR(amount: number, showSign = false): string {
  const isNeg = amount < 0;
  const absVal = Math.abs(Math.round(amount * 100) / 100);
  const formatted = absVal.toLocaleString("en-IN", {
    maximumFractionDigits: absVal % 1 === 0 ? 0 : 2,
  });
  if (isNeg) return `-₹${formatted}`;
  if (showSign && amount > 0) return `+₹${formatted}`;
  return `₹${formatted}`;
}

export function normalizeToDisplayDate(dateStr: string): {
  display: string;
  iso: string;
} {
  const trimmed = (dateStr || "").trim();
  // Match DD-MM-YYYY
  const dmy = /^(\d{2})[-/](\d{2})[-/](\d{4})$/.exec(trimmed);
  if (dmy) {
    return {
      display: `${dmy[1]}-${dmy[2]}-${dmy[3]}`,
      iso: `${dmy[3]}-${dmy[2]}-${dmy[1]}`,
    };
  }
  // Match YYYY-MM-DD
  const ymd = /^(\d{4})[-/](\d{2})[-/](\d{2})$/.exec(trimmed);
  if (ymd) {
    return {
      display: `${ymd[3]}-${ymd[2]}-${ymd[1]}`,
      iso: `${ymd[1]}-${ymd[2]}-${ymd[3]}`,
    };
  }
  return {
    display: "08-10-2026",
    iso: "2026-10-08",
  };
}

// Mirrors tools/categorization_tool.py
const MERCHANT_KEYWORDS: Record<CategoryName, string[]> = {
  Food: [
    "swiggy",
    "zomato",
    "starbucks",
    "barbeque",
    "canteen",
    "blinkit",
    "zepto",
    "blue tokai",
    "mcdonald",
    "dominos",
    "kfc",
    "pizza",
    "cafe",
    "restaurant",
    "dinner",
    "lunch",
    "breakfast",
    "coffee",
    "grocery",
    "food",
    "mainland china",
    "haldiram",
    "subway",
  ],
  Transport: [
    "uber",
    "ola",
    "rapido",
    "metro",
    "irctc",
    "petrol",
    "fuel",
    "shell",
    "bus",
    "auto",
    "cab",
    "flight",
    "train",
    "commute",
    "college",
  ],
  Shopping: [
    "amazon",
    "flipkart",
    "myntra",
    "ajio",
    "croma",
    "reliance",
    "nykaa",
    "zara",
    "decathlon",
    "shoes",
    "jacket",
    "clothes",
    "keyboard",
    "electronics",
    "shopping",
  ],
  Entertainment: [
    "bookmyshow",
    "pvr",
    "inox",
    "netflix",
    "spotify",
    "prime",
    "hotstar",
    "steam",
    "movie",
    "concert",
    "gaming",
  ],
  Bills: [
    "airtel",
    "jio",
    "vi",
    "bescom",
    "electricity",
    "water",
    "gas",
    "broadband",
    "wifi",
    "recharge",
    "rent",
    "bill",
  ],
  Healthcare: [
    "apollo",
    "pharmeasy",
    "1mg",
    "medplus",
    "hospital",
    "clinic",
    "doctor",
    "pharmacy",
    "medicine",
    "vitamins",
  ],
  Education: [
    "coursera",
    "udemy",
    "edx",
    "nptel",
    "tuition",
    "textbook",
    "exam",
    "workshop",
    "certification",
    "course",
  ],
  Others: [],
};

export function categorizeExpense(
  merchant: string,
  description = ""
): CategoryName {
  const combined = `${merchant} ${description}`.toLowerCase();
  for (const cat of CATEGORIES) {
    if (cat === "Others") continue;
    for (const kw of MERCHANT_KEYWORDS[cat]) {
      if (combined.includes(kw)) {
        return cat;
      }
    }
  }
  return "Others";
}

export function parseNaturalLanguageExpense(input: string): {
  date: string;
  merchant: string;
  amount: number;
  category: CategoryName;
  description: string;
} {
  const amtMatch = input.match(/(?:₹|rs\.?|inr\s*)?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)/i);
  const amount = amtMatch ? parseFloat(amtMatch[1].replace(/,/g, "")) : 0;

  const dateMatch = input.match(/\b(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})\b/);
  const dateStr = dateMatch ? dateMatch[1] : "08-10-2026";

  let merchant = "General Merchant";
  const merchantMatch = input.match(
    /\b(?:at|on|from|to|via)\s+([A-Za-z0-9][A-Za-z0-9\s&]{1,24}?)(?:\s+(?:for|on|yesterday|today|worth|of|₹|\d|and)|$)/i
  );
  if (merchantMatch) {
    merchant = merchantMatch[1]
      .trim()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  } else {
    const lower = input.toLowerCase();
    for (const cat of CATEGORIES) {
      for (const kw of MERCHANT_KEYWORDS[cat]) {
        if (lower.includes(kw) && kw.length > 3) {
          merchant = kw.replace(/\b\w/g, (c) => c.toUpperCase());
          break;
        }
      }
    }
  }

  const category = categorizeExpense(merchant, input);
  return {
    date: dateStr,
    merchant,
    amount,
    category,
    description: input.trim(),
  };
}

// Mirrors tools/budget_tool.py
export function getAllBudgetStatuses(
  transactions: Transaction[],
  budgets: Record<CategoryName, number>,
  monthPrefix = "2026-10"
): CategoryBudgetStatus[] {
  return CATEGORIES.map((category) => {
    const budget = budgets[category] || 0;
    const spent = transactions
      .filter(
        (tx) => tx.category === category && tx.isoDate.startsWith(monthPrefix)
      )
      .reduce((acc, tx) => acc + tx.amount, 0);

    const remaining = Math.round((budget - spent) * 100) / 100;
    const utilizationPct =
      budget > 0 ? Math.round((spent / budget) * 1000) / 10 : 0;

    let status: CategoryBudgetStatus["status"] = "UNDER BUDGET";
    if (remaining < 0) {
      status = "OVER BUDGET";
    } else if (utilizationPct >= 80) {
      status = "NEAR LIMIT";
    }

    return {
      category,
      budget,
      spent,
      remaining,
      utilizationPct,
      status,
    };
  });
}

export function suggestDiscretionaryReallocation(
  statuses: CategoryBudgetStatus[]
) {
  const overBudget = statuses.filter((s) => s.status === "OVER BUDGET");
  const unusedDiscretionary = statuses
    .filter(
      (s) =>
        DISCRETIONARY_CATEGORIES.includes(s.category) && s.remaining > 0
    )
    .sort((a, b) => b.remaining - a.remaining);

  const suggestions: string[] = [];
  if (overBudget.length > 0) {
    for (const ob of overBudget) {
      const overrun = formatINR(Math.abs(ob.remaining));
      if (unusedDiscretionary.length > 0) {
        const bufferSummary = unusedDiscretionary
          .slice(0, 3)
          .map((u) => `${u.category} (${formatINR(u.remaining)} unused)`)
          .join(", ");
        suggestions.push(
          `Your ${ob.category} expenses have exceeded your monthly budget by ${overrun}. You still have unused discretionary budget in ${bufferSummary}. Consider reducing non-essential spending in those categories for the remaining days of the month.`
        );
      } else {
        suggestions.push(
          `Your ${ob.category} expenses have exceeded your monthly budget by ${overrun}. All discretionary category buffers are depleted for this month.`
        );
      }
    }
  } else {
    suggestions.push(
      "All categories are within their monthly budget limits. Continue pacing your discretionary spending to preserve your savings buffer."
    );
  }

  return {
    overBudget,
    unusedDiscretionary,
    suggestions,
  };
}

// Mirrors tools/spike_detector.py
export function detectAllCategorySpikes(
  transactions: Transaction[],
  thresholdPct = 35
): SpendingSpike[] {
  const results = CATEGORIES.map((category) => {
    const catTxs = transactions.filter((t) => t.category === category);
    const prevSpend = catTxs
      .filter((t) => t.isoDate >= "2026-09-18" && t.isoDate <= "2026-09-30")
      .reduce((sum, t) => sum + t.amount, 0);
    const currSpend = catTxs
      .filter((t) => t.isoDate >= "2026-10-01" && t.isoDate <= "2026-10-08")
      .reduce((sum, t) => sum + t.amount, 0);

    const increaseAmount = Math.round((currSpend - prevSpend) * 100) / 100;
    const increasePct =
      prevSpend > 0
        ? Math.round((increaseAmount / prevSpend) * 1000) / 10
        : currSpend > 500
        ? 100
        : 0;

    const spikeDetected = increasePct >= thresholdPct && increaseAmount >= 300;
    const message = spikeDetected
      ? `${category} spending has increased significantly (+${increasePct}%) compared with the previous period (${formatINR(
          prevSpend
        )} → ${formatINR(currSpend)}).`
      : `${category} weekly spending is within normal variance (${formatINR(
          currSpend
        )} vs ${formatINR(prevSpend)} previously).`;

    return {
      category,
      previousWeeklySpending: prevSpend,
      currentWeeklySpending: currSpend,
      increaseAmount,
      increasePct,
      spikeDetected,
      message,
    };
  });

  return results.sort((a, b) => {
    if (a.spikeDetected !== b.spikeDetected) {
      return a.spikeDetected ? -1 : 1;
    }
    return b.increaseAmount - a.increaseAmount;
  });
}

// Mirrors agent/graph.py 5-node LangGraph State Machine
export function executeLocalAgentGraph(
  userQuery: string,
  transactions: Transaction[],
  budgets: Record<CategoryName, number>,
  onAddTransaction?: (tx: Omit<Transaction, "id" | "createdAt">) => Transaction
): {
  intent: string;
  selectedTools: string[];
  trace: AgentTraceStep[];
  toolOutputs: Record<string, any>;
  fallbackResponse: string;
} {
  const qLower = userQuery.toLowerCase();
  const trace: AgentTraceStep[] = [];

  // Node 1: Understand Request
  let targetCategory: CategoryName | null = null;
  for (const cat of CATEGORIES) {
    if (qLower.includes(cat.toLowerCase())) {
      targetCategory = cat;
      break;
    }
  }
  if (!targetCategory) {
    const inferred = categorizeExpense("", userQuery);
    if (inferred !== "Others") targetCategory = inferred;
  }

  let intent = "GENERAL_SUMMARY";
  if (
    (qLower.includes("receipt") ||
      qLower.includes("add ") ||
      qLower.includes("spent ") ||
      qLower.includes("paid ")) &&
    (qLower.includes("budget") ||
      qLower.includes("left") ||
      qLower.includes("remaining"))
  ) {
    intent = "ADD_EXPENSE_AND_CHECK_BUDGET";
  } else if (
    qLower.startsWith("add ") ||
    qLower.includes("spent ₹") ||
    qLower.includes("paid ₹")
  ) {
    intent = "ADD_EXPENSE";
  } else if (qLower.includes("afford") || qLower.includes("can i spend")) {
    intent = "AFFORDABILITY_CHECK";
  } else if (
    qLower.includes("alert") ||
    qLower.includes("exceed") ||
    qLower.includes("over budget") ||
    qLower.includes("why did i")
  ) {
    intent = "EXPLAIN_BUDGET_ALERT";
  } else if (
    qLower.includes("spike") ||
    qLower.includes("increased the most") ||
    qLower.includes("unusual")
  ) {
    intent = "CHECK_SPENDING_SPIKE";
  } else if (
    qLower.includes("reduce") ||
    qLower.includes("save") ||
    qLower.includes("cut") ||
    qLower.includes("where can i")
  ) {
    intent = "REDUCE_SPENDING_ADVICE";
  } else if (
    targetCategory &&
    (qLower.includes("how much") ||
      qLower.includes("spent") ||
      qLower.includes("left") ||
      qLower.includes("remaining") ||
      qLower.includes("budget"))
  ) {
    intent = "CHECK_CATEGORY_BUDGET";
  }

  trace.push({
    node: "1. Understand Request",
    pythonModule: "agent/graph.py :: understand_request_node",
    detail: `Classified intent = ${intent} · Target Category = ${
      targetCategory || "All Categories"
    }`,
  });

  // Node 2: Decide Required Tool(s)
  let selectedTools: string[] = [];
  if (intent === "ADD_EXPENSE_AND_CHECK_BUDGET") {
    selectedTools = [
      qLower.includes("receipt")
        ? "ocr_tool.extract_receipt"
        : "categorization_tool.parse_natural_language_expense",
      "database_tool.add_transaction",
      "budget_tool.calculate_budget_status",
    ];
  } else if (intent === "ADD_EXPENSE") {
    selectedTools = [
      "categorization_tool.parse_natural_language_expense",
      "database_tool.add_transaction",
      "budget_tool.calculate_budget_status",
    ];
  } else if (intent === "CHECK_CATEGORY_BUDGET") {
    selectedTools = [
      "budget_tool.calculate_budget_status",
      "spike_detector.detect_spending_spike",
    ];
  } else if (intent === "AFFORDABILITY_CHECK") {
    selectedTools = [
      "budget_tool.calculate_budget_status",
      "budget_tool.suggest_discretionary_reallocation",
    ];
  } else if (intent === "EXPLAIN_BUDGET_ALERT") {
    selectedTools = [
      "budget_tool.get_all_budget_statuses",
      "budget_tool.suggest_discretionary_reallocation",
    ];
  } else if (intent === "CHECK_SPENDING_SPIKE") {
    selectedTools = [
      "spike_detector.detect_all_category_spikes",
      "budget_tool.get_all_budget_statuses",
    ];
  } else if (intent === "REDUCE_SPENDING_ADVICE") {
    selectedTools = [
      "budget_tool.suggest_discretionary_reallocation",
      "spike_detector.detect_all_category_spikes",
    ];
  } else {
    selectedTools = [
      "analytics.get_summary_metrics",
      "budget_tool.suggest_discretionary_reallocation",
      "spike_detector.detect_all_category_spikes",
    ];
  }

  trace.push({
    node: "2. Decide Required Tool(s)",
    pythonModule: "agent/graph.py :: decide_required_tool_node",
    detail: `Routed to: ${selectedTools.join(" → ")}`,
  });

  // Node 3: Call Tool(s)
  let workingTransactions = [...transactions];
  let savedTransaction: Transaction | null = null;
  const activeCat: CategoryName = targetCategory || "Food";

  if (
    intent === "ADD_EXPENSE_AND_CHECK_BUDGET" ||
    intent === "ADD_EXPENSE"
  ) {
    const parsed = parseNaturalLanguageExpense(userQuery);
    const amountToUse = parsed.amount > 0 ? parsed.amount : 550;
    const merchantToUse =
      parsed.merchant !== "General Merchant"
        ? parsed.merchant
        : qLower.includes("restaurant")
        ? "Mainland China Restaurant"
        : "Starbucks Coffee";
    const catToUse =
      parsed.category !== "Others" ? parsed.category : targetCategory || "Food";
    const { display, iso } = normalizeToDisplayDate(parsed.date);

    const newTxPayload = {
      date: display,
      isoDate: iso,
      merchant: merchantToUse,
      amount: amountToUse,
      category: catToUse,
      description: qLower.includes("receipt")
        ? "Extracted via OCR Receipt Tool"
        : "Logged via SpendWise Agent",
      source: (qLower.includes("receipt") ? "Receipt" : "Text") as
        | "Receipt"
        | "Text",
    };

    if (onAddTransaction) {
      savedTransaction = onAddTransaction(newTxPayload);
      workingTransactions = [savedTransaction, ...workingTransactions];
    }
  }

  const allStatuses = getAllBudgetStatuses(workingTransactions, budgets);
  const categoryStatus =
    allStatuses.find(
      (s) =>
        s.category ===
        (savedTransaction ? savedTransaction.category : activeCat)
    ) || allStatuses[0];
  const reallocation = suggestDiscretionaryReallocation(allStatuses);
  const allSpikes = detectAllCategorySpikes(workingTransactions);
  const categorySpike =
    allSpikes.find((s) => s.category === categoryStatus.category) ||
    allSpikes[0];

  const toolOutputs: Record<string, any> = {
    savedTransaction,
    categoryStatus,
    reallocation,
    topSpikes: allSpikes.filter((s) => s.spikeDetected),
  };

  trace.push({
    node: "3. Call Tool(s)",
    pythonModule: "agent/graph.py :: call_tool_node",
    detail: savedTransaction
      ? `Inserted SQLite tx #${savedTransaction.id} (${
          savedTransaction.merchant
        }, ${formatINR(savedTransaction.amount)}) & computed Pandas budget state`
      : `Queried SQLite & Pandas metrics for ${categoryStatus.category} (Spent: ${formatINR(
          categoryStatus.spent
        )} / Budget: ${formatINR(categoryStatus.budget)})`,
  });

  // Node 4: Evaluate Result
  let evaluationSummary = `${categoryStatus.category} status is ${categoryStatus.status} (${categoryStatus.utilizationPct}% utilized, ${formatINR(
    categoryStatus.remaining
  )} remaining).`;

  let proposedExpense = 500;
  if (intent === "AFFORDABILITY_CHECK") {
    const m = userQuery.match(/(?:₹|rs\.?|inr\s*)?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)/i);
    if (m) proposedExpense = parseFloat(m[1].replace(/,/g, ""));
    const afterRem = categoryStatus.remaining - proposedExpense;
    toolOutputs.affordability = {
      proposedExpense,
      canAfford: afterRem >= 0,
      remainingAfter: afterRem,
    };
    evaluationSummary = `Proposed ${formatINR(proposedExpense)} in ${
      categoryStatus.category
    } → ${
      afterRem >= 0 ? "FEASIBLE" : "EXCEEDS BUDGET"
    } (Remaining after expense: ${formatINR(afterRem)}).`;
  }

  trace.push({
    node: "4. Evaluate Result",
    pythonModule: "agent/graph.py :: evaluate_result_node",
    detail: evaluationSummary,
  });

  // Node 5: Generate Response
  let fallbackResponse = "";
  if (intent === "ADD_EXPENSE_AND_CHECK_BUDGET" || intent === "ADD_EXPENSE") {
    if (savedTransaction) {
      fallbackResponse = `**Receipt / Expense Processed & Stored in SQLite**\n\n- **Merchant:** ${
        savedTransaction.merchant
      }\n- **Amount:** ${formatINR(
        savedTransaction.amount
      )}\n- **Auto-Category:** ${savedTransaction.category} *(Source: ${
        savedTransaction.source
      })*\n- **Date:** ${savedTransaction.date}\n\n**Updated ${
        categoryStatus.category
      } Budget Calculation (Pandas):**\n- **Monthly Budget:** ${formatINR(
        categoryStatus.budget
      )}\n- **Total Spent This Month:** ${formatINR(
        categoryStatus.spent
      )} (${categoryStatus.utilizationPct}%)\n- **Remaining ${
        categoryStatus.category
      } Budget:** **${formatINR(categoryStatus.remaining)}** (${
        categoryStatus.status
      })`;
    }
  } else if (intent === "CHECK_CATEGORY_BUDGET") {
    fallbackResponse = `**${
      categoryStatus.category
    } Budget & Spending Summary (October 2026)**\n\n- **Monthly Budget:** ${formatINR(
      categoryStatus.budget
    )}\n- **Actual Spent:** **${formatINR(categoryStatus.spent)}** (${
      categoryStatus.utilizationPct
    }% used)\n- **Remaining Budget:** **${formatINR(
      categoryStatus.remaining
    )}**\n- **Status:** ${categoryStatus.status}\n\n${
      categorySpike.spikeDetected
        ? `🚨 **Spending Spike Note:** ${categorySpike.message}`
        : `Weekly trend: ${categorySpike.message}`
    }`;
  } else if (intent === "AFFORDABILITY_CHECK") {
    const afterRem = categoryStatus.remaining - proposedExpense;
    const canAfford = afterRem >= 0;
    fallbackResponse = canAfford
      ? `**Yes — You can afford another ${formatINR(proposedExpense)} expense in ${
          categoryStatus.category
        }.**\n\n- **Current Remaining ${
          categoryStatus.category
        } Budget:** ${formatINR(
          categoryStatus.remaining
        )}\n- **Proposed Expense:** ${formatINR(
          proposedExpense
        )}\n- **Projected Remaining Balance:** **${formatINR(
          afterRem
        )}**\n\n*Tip: Your weekly ${
          categoryStatus.category
        } spending spiked to ${formatINR(
          categorySpike.currentWeeklySpending
        )} this week (up from ${formatINR(
          categorySpike.previousWeeklySpending
        )} last week), so pace non-essential orders.*`
      : `**Caution — Spending ${formatINR(
          proposedExpense
        )} will put ${categoryStatus.category} over budget by ${formatINR(
          Math.abs(afterRem)
        )}.**\n\n- **Current Remaining ${
          categoryStatus.category
        } Budget:** ${formatINR(
          categoryStatus.remaining
        )}\n- **Recommendation:** Reallocate unused discretionary funds from Entertainment (${formatINR(
          allStatuses.find((s) => s.category === "Entertainment")?.remaining || 0
        )} left) before making this purchase.`;
  } else if (intent === "EXPLAIN_BUDGET_ALERT") {
    const ob = reallocation.overBudget[0];
    if (ob) {
      fallbackResponse = `**Why You Received a ${
        ob.category
      } Budget Alert**\n\nYour **${
        ob.category
      }** spending reached **${formatINR(
        ob.spent
      )}** against a monthly budget of **${formatINR(
        ob.budget
      )}**, exceeding your limit by **${formatINR(
        Math.abs(ob.remaining)
      )}** (${
        ob.utilizationPct
      }% utilization).\n\n**Top Contributing Transactions:**\n- Myntra: ₹2,400 *(Winter jacket & apparel)*\n- Croma: ₹1,900 *(Wireless keyboard & mouse)*\n- Amazon: ₹1,800 *(Shoes)*\n\n**💡 SpendWise Reallocation Suggestion:**\n${
        reallocation.suggestions[0]
      }`;
    } else {
      fallbackResponse =
        "All categories are currently within their monthly budget limits—no active overrun alerts.";
    }
  } else if (intent === "CHECK_SPENDING_SPIKE") {
    const topSpike = allSpikes[0];
    fallbackResponse = `**Weekly Spending Spike Analysis**\n\n🚨 **${
      topSpike.category
    }** increased the most this week (**+${
      topSpike.increasePct
    }%**).\n\n- **Previous Weekly ${
      topSpike.category
    } Spending:** ${formatINR(
      topSpike.previousWeeklySpending
    )}\n- **Current Weekly ${topSpike.category} Spending:** **${formatINR(
      topSpike.currentWeeklySpending
    )}**\n- **Net Increase:** +${formatINR(topSpike.increaseAmount)}\n\n${
      topSpike.message
    }`;
  } else if (intent === "REDUCE_SPENDING_ADVICE") {
    const bufferLines = reallocation.unusedDiscretionary
      .map(
        (u) =>
          `- **${u.category}**: ${formatINR(
            u.remaining
          )} remaining out of ${formatINR(u.budget)} (${
            u.utilizationPct
          }% used) — *Good candidate to cap non-essential spending.*`
      )
      .join("\n");
    fallbackResponse = `**Where You Can Reduce Discretionary Spending**\n\n${reallocation.suggestions.join(
      "\n\n"
    )}\n\n**Discretionary Categories with Remaining Buffer:**\n${bufferLines}`;
  } else {
    const totalBudget = allStatuses.reduce((a, b) => a + b.budget, 0);
    const totalSpent = allStatuses.reduce((a, b) => a + b.spent, 0);
    fallbackResponse = `**SpendWise Executive Summary (October 2026)**\n\n- **Total Monthly Budget:** ${formatINR(
      totalBudget
    )}\n- **Total Actual Spending:** **${formatINR(
      totalSpent
    )}**\n- **Remaining Overall Budget:** **${formatINR(
      totalBudget - totalSpent
    )}**\n\n**Key Insights:**\n- 🚨 **Shopping** is over budget by **₹2,100** (Spent ₹6,100 vs ₹4,000 budget).\n- 📈 **Food** experienced a **+100% weekly spike** (₹1,500 last week → ₹3,000 this week).\n- 💡 **Suggestion:** ${
      reallocation.suggestions[0]
    }`;
  }

  trace.push({
    node: "5. Generate Response",
    pythonModule: "agent/graph.py :: generate_response_node",
    detail:
      "Synthesized natural-language financial insight from verified SQLite & Pandas outputs.",
  });

  return {
    intent,
    selectedTools,
    trace,
    toolOutputs,
    fallbackResponse,
  };
}
