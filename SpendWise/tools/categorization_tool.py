"""
SpendWise — Expense Categorization & Natural Language Parsing Tool
==================================================================
Owner: Member 2 (Database + Categorization)

Responsibility:
- Automatically assigns one of the 8 official categories (`Food`, `Transport`,
  `Shopping`, `Entertainment`, `Bills`, `Healthcare`, `Education`, `Others`)
  based on merchant name and transaction description.
- Parses natural language expense strings (e.g., "Spent 450 on Swiggy for dinner")
  into structured transaction dictionaries.
- INTEGRATION POINT: ChromaDB semantic similarity search over historical merchant
  embeddings + LLM fallback for unseen merchants.
"""

import re
from datetime import datetime
from typing import Dict, Any

from utils.helpers import CATEGORIES

# Deterministic keyword taxonomy for fast, zero-latency baseline categorization
MERCHANT_CATEGORY_KEYWORDS: Dict[str, list[str]] = {
    "Food": [
        "swiggy", "zomato", "starbucks", "barbeque", "canteen", "blinkit",
        "zepto", "blue tokai", "mcdonald", "dominos", "kfc", "pizza", "cafe",
        "restaurant", "dinner", "lunch", "breakfast", "coffee", "grocery", "food",
        "mainland china", "haldiram", "subway"
    ],
    "Transport": [
        "uber", "ola", "rapido", "metro", "irctc", "petrol", "fuel", "shell",
        "hpcl", "bus", "auto", "cab", "flight", "indigo", "train", "commute", "college"
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "croma", "reliance digital",
        "nykaa", "zara", "h&m", "decathlon", "shoes", "jacket", "clothes",
        "keyboard", "electronics", "mall", "shopping"
    ],
    "Entertainment": [
        "bookmyshow", "pvr", "inox", "netflix", "spotify", "prime video",
        "hotstar", "steam", "playstation", "movie", "concert", "gaming", "bowling"
    ],
    "Bills": [
        "airtel", "jio", "vi", "bescom", "electricity", "water", "gas",
        "broadband", "wifi", "recharge", "rent", "maintenance", "bill"
    ],
    "Healthcare": [
        "apollo", "pharmeasy", "1mg", "medplus", "hospital", "clinic",
        "doctor", "pharmacy", "medicine", "vitamins", "dental", "lab test"
    ],
    "Education": [
        "coursera", "udemy", "edx", "unstop", "nptel", "tuition", "college fee",
        "textbook", "exam", "workshop", "certification", "library", "course"
    ],
}


def categorize_expense(merchant: str, description: str = "") -> str:
    """
    Categorize an expense based on merchant name and description.

    FUTURE INTEGRATION POINT (ChromaDB + LLM):
    1. Query ChromaDB collection `merchant_categories` for nearest semantic match.
    2. If distance > threshold, invoke LLM classifier with `CATEGORIES`.
    3. Fallback to deterministic keyword lookup below.
    """
    combined_text = f"{merchant} {description}".lower().strip()

    for category, keywords in MERCHANT_CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in combined_text:
                return category

    return "Others"


def parse_natural_language_expense(user_text: str) -> Dict[str, Any]:
    """
    Parse a natural-language expense statement into a structured transaction dictionary.
    Example input: "Spent ₹450 at Swiggy for late night dinner on 01-10-2026"
    """
    # Extract amount (supports ₹450, Rs 450, 450.50, etc.)
    amount_match = re.search(r"(?:₹|rs\.?|inr\s*)?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)", user_text, re.IGNORECASE)
    amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

    # Extract date if present (DD-MM-YYYY or YYYY-MM-DD), else default to today
    date_match = re.search(r"\b(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})\b", user_text)
    tx_date = date_match.group(1) if date_match else datetime.now().strftime("%d-%m-%Y")

    # Extract merchant heuristic ("at <Merchant>", "on <Merchant>", "from <Merchant>", "to <Merchant>")
    merchant = "General Merchant"
    merchant_match = re.search(
        r"\b(?:at|on|from|to|via)\s+([A-Za-z0-9][A-Za-z0-9\s&]{1,24}?)(?:\s+(?:for|on|yesterday|today|worth|of|₹|\d)|$)",
        user_text,
        re.IGNORECASE,
    )
    if merchant_match:
        merchant = merchant_match.group(1).strip().title()
    else:
        # Check if any known merchant keyword appears in text
        lower_text = user_text.lower()
        for cat, keywords in MERCHANT_CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in lower_text and len(kw) > 3:
                    merchant = kw.title()
                    break

    category = categorize_expense(merchant, user_text)

    return {
        "date": tx_date,
        "merchant": merchant,
        "amount": amount,
        "category": category,
        "description": user_text.strip(),
        "source": "Text",
    }
