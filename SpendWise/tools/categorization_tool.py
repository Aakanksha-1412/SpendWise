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
- Semantic memory (ChromaDB): when the keyword list doesn't know a merchant, ChromaDB
  finds the category by MEANING (e.g. "Chai Point" ~ tea/coffee -> Food), and it learns
  every merchant -> category pair the user saves (see `remember_merchant_category`).
  Runs locally (no API key); stored in CHROMA_PERSIST_DIR (default data/chroma_memory).
"""

import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

from utils.helpers import CATEGORIES

logger = logging.getLogger(__name__)

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


# Plain-language descriptions of each category. ChromaDB compares a merchant's name with
# these by meaning, so unseen merchants with a meaningful name still get a category.
CATEGORY_DESCRIPTIONS: Dict[str, list[str]] = {
    "Food": [
        "restaurant meal dinner lunch breakfast", "tea chai coffee cafe snacks bakery",
        "biryani pizza burger dosa thali food", "groceries vegetables fruits supermarket",
        "food delivery order",
    ],
    "Transport": ["taxi cab auto rickshaw ride", "bus train metro ticket", "petrol diesel fuel", "flight airline travel"],
    "Shopping": [
        "clothes shoes fashion apparel", "electronics gadgets phone laptop", "online shopping order",
        "glasses spectacles watch accessories", "cosmetics beauty makeup",
    ],
    "Entertainment": ["movie cinema film tickets", "music video streaming subscription", "video games gaming", "concert event party"],
    "Bills": ["electricity water gas bill", "mobile recharge internet broadband", "house rent maintenance", "insurance premium"],
    "Healthcare": ["doctor clinic hospital", "medicine pharmacy chemist", "gym fitness workout", "dental eye checkup lab test"],
    "Education": ["online course learning classes", "college fees tuition exam", "coaching test preparation", "textbooks study material"],
}

# Cosine distance: 0 = same meaning, 1 = unrelated. Above this, the match isn't trusted
# and the expense stays "Others" (e.g. "XYZ Traders" has no meaningful words).
SEMANTIC_MATCH_MAX_DISTANCE = 0.72
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_open_memories: Dict[str, Any] = {}


def categorize_expense(merchant: str, description: str = "") -> str:
    """
    Categorize an expense based on merchant name and description:
    1. Fast keyword lookup (MERCHANT_CATEGORY_KEYWORDS).
    2. If no keyword matches: ChromaDB semantic memory (learned merchants + category descriptions).
    3. Otherwise "Others".
    """
    combined_text = f"{merchant} {description}".lower().strip()

    for category, keywords in MERCHANT_CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in combined_text:
                return category

    return semantic_category(merchant, description) or "Others"


def _merchant_memory():
    """Open the ChromaDB collection once (seeding the category descriptions). None if unavailable."""
    path = os.getenv("CHROMA_PERSIST_DIR") or os.path.join("data", "chroma_memory")
    if not os.path.isabs(path):
        path = os.path.join(_PROJECT_DIR, path)
    if path not in _open_memories:
        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))
            collection = client.get_or_create_collection("merchant_categories", metadata={"hnsw:space": "cosine"})
            entries = [(cat, i, text) for cat, texts in CATEGORY_DESCRIPTIONS.items() for i, text in enumerate(texts)]
            collection.upsert(
                ids=[f"description:{cat}:{i}" for cat, i, _ in entries],
                documents=[text for _, _, text in entries],
                metadatas=[{"category": cat, "kind": "description"} for cat, _, _ in entries],
            )
            _open_memories[path] = collection
        except Exception as exc:  # ChromaDB missing, model download failed, disk problem ...
            logger.warning("ChromaDB merchant memory unavailable, using keywords only: %r", exc)
            _open_memories[path] = None
    return _open_memories[path]


def semantic_category(merchant: str, description: str = "") -> Optional[str]:
    """Closest category by meaning, or None if ChromaDB isn't sure (or isn't available)."""
    memory = _merchant_memory()
    queries = [text for text in dict.fromkeys([merchant.strip(), f"{merchant} {description}".strip()]) if text]
    if memory is None or not queries:
        return None
    try:
        result = memory.query(query_texts=queries, n_results=1)
    except Exception as exc:
        logger.warning("ChromaDB query failed: %r", exc)
        return None
    best = min(
        (
            (distances[0], metadatas[0]["category"])
            for distances, metadatas in zip(result["distances"], result["metadatas"])
            if distances
        ),
        default=None,
    )
    if best is None or best[0] > SEMANTIC_MATCH_MAX_DISTANCE:
        return None
    return best[1]


def remember_merchant_category(merchant: str, category: str) -> None:
    """
    Teach the semantic memory that `merchant` belongs to `category` (called whenever an
    expense is saved), so the same or similar merchants are recognised next time.
    """
    name = (merchant or "").strip()
    if not name or category not in CATEGORIES or category == "Others":
        return
    memory = _merchant_memory()
    if memory is None:
        return
    try:
        memory.upsert(
            ids=[f"merchant:{name.lower()}"],
            documents=[name],
            metadatas=[{"category": category, "kind": "learned"}],
        )
    except Exception as exc:
        logger.warning("ChromaDB could not remember %r: %r", name, exc)


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
