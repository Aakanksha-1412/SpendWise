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
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from database.database import current_user_id
from utils.helpers import CATEGORIES, normalize_date

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
        "hpcl", "bus", "auto", "cab", "flight", "indigo", "train", "commute"
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "croma", "reliance digital",
        "nykaa", "zara", "h&m", "decathlon", "shoes", "jacket", "clothes",
        "keyboard", "electronics", "mall", "shopping", "metro shoes"
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
        "coursera", "udemy", "edx", "unstop", "nptel", "tuition", "college fee", "college",
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

# Cosine distance: 0 = same meaning, 1 = unrelated. Above these limits a match isn't trusted
# and the expense stays "Others".
# - Category descriptions have real meaning ("tea chai coffee"), so a looser limit works.
# - Learned merchant NAMES are mostly meaningless brand names: unrelated names still score
#   ~0.6 ("XYZ Traders" vs "Zomato"), while the same shop spelled differently scores <= 0.25
#   ("Physics Wallah" vs "PhysicsWallah"). So learned names must be nearly identical.
DESCRIPTION_MATCH_MAX_DISTANCE = 0.62
LEARNED_NAME_MATCH_MAX_DISTANCE = 0.35
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_open_memories: Dict[str, Any] = {}
_memory_version = 0  # goes up whenever a merchant is learned (lets callers refresh caches)


def categorize_expense(merchant: str, description: str = "", use_semantic: bool = True) -> str:
    """
    Categorize an expense based on merchant name and description:
    1. Fast keyword lookup (MERCHANT_CATEGORY_KEYWORDS).
    2. If no keyword matches and use_semantic: ChromaDB semantic memory
       (learned merchants + category descriptions).
    3. Otherwise "Others".
    """
    # The shop name decides first; the description only when the name has no keyword
    category = _keyword_category(merchant) or _keyword_category(description)
    if category:
        return category

    if not use_semantic:
        return "Others"
    return semantic_category(merchant, description) or "Others"


def _keyword_category(text: str) -> Optional[str]:
    """
    Category of the longest keyword found in `text` as a whole word (plural allowed), so
    "vi" doesn't match "multivitamin" and "metro shoes" beats "metro". None if none match.
    """
    text = (text or "").lower()
    best_category, best_length = None, 0
    for category, keywords in MERCHANT_CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if len(kw) > best_length and re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?:s|es)?(?![a-z0-9])", text):
                best_category, best_length = category, len(kw)
    return best_category


def merchant_memory_version() -> int:
    """A number that changes every time ChromaDB learns a merchant."""
    return _memory_version


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
        # 1. A shop the user already saved: exact lookup by name (no similarity search needed)
        if merchant.strip():
            exact = memory.get(ids=[f"merchant:{current_user_id()}:{merchant.strip().lower()}"])
            if exact["ids"]:
                return exact["metadatas"][0]["category"]
        # 2. Otherwise: closest meaning among learned shops and category descriptions
        # Category descriptions are shared; learned shops only from THIS user
        result = memory.query(
            query_texts=queries,
            n_results=5,
            where={"$or": [{"kind": "description"}, {"user_id": current_user_id()}]},
        )
    except Exception as exc:
        logger.warning("ChromaDB query failed: %r", exc)
        return None
    limits = {"description": DESCRIPTION_MATCH_MAX_DISTANCE, "learned": LEARNED_NAME_MATCH_MAX_DISTANCE}
    trusted = [
        (distance, metadata["category"])
        for distances, metadatas in zip(result["distances"], result["metadatas"])
        for distance, metadata in zip(distances, metadatas)
        if distance <= limits.get(metadata.get("kind"), 0.0)
    ]
    return min(trusted)[1] if trusted else None


def remember_merchant_category(merchant: str, category: str) -> None:
    """
    Teach the semantic memory that `merchant` belongs to `category` (called whenever an
    expense is saved), so the same or similar merchants are recognised next time.
    """
    remember_merchant_categories([(merchant, category)])


def remember_merchant_categories(pairs: List[Tuple[str, str]]) -> None:
    """Teach many (merchant, category) pairs in ONE ChromaDB write (used by CSV import)."""
    learned: Dict[str, Tuple[str, str]] = {}
    for merchant, category in pairs:
        name = (merchant or "").strip()
        if name and category in CATEGORIES and category != "Others":
            learned[name.lower()] = (name, category)  # last one wins for repeated merchants
    if not learned:
        return
    memory = _merchant_memory()
    if memory is None:
        return
    user_id = current_user_id()  # each user's learned shops are kept separate
    global _memory_version
    try:
        memory.upsert(
            ids=[f"merchant:{user_id}:{key}" for key in learned],
            documents=[name for name, _ in learned.values()],
            metadatas=[{"category": category, "kind": "learned", "user_id": user_id} for _, category in learned.values()],
        )
        _memory_version += 1
    except Exception as exc:
        logger.warning("ChromaDB could not remember %d merchants: %r", len(learned), exc)


INCOME_WORDS = re.compile(r"\b(?:refund|refunded|received|receive|credited|cashback|cash back|salary)\b", re.IGNORECASE)
INCOME_NOT_SAVED = (
    "This looks like money you received, not money you spent, so it was not saved. "
    "SpendWise only tracks expenses."
)


def parse_natural_language_expense(user_text: str) -> Dict[str, Any]:
    """
    Parse a natural-language expense statement into a structured transaction dictionary.
    Example input: "Spent ₹450 at Swiggy for late night dinner on 01-10-2026"
    """
    # Extract date first: DD-MM-YYYY (also with / or .), YYYY-MM-DD, or "yesterday" / "today";
    # default today. It is then removed, so its digits can't be taken as the amount.
    date_match = re.search(r"\b(\d{1,2}[-/.]\d{1,2}[-/.]\d{4}|\d{4}-\d{2}-\d{2})\b", user_text)
    text_without_date = user_text
    if date_match:
        text_without_date = user_text[: date_match.start()] + " " + user_text[date_match.end():]

    # Extract amount. Prefer a number marked as money (₹450, Rs 450, 450 rupees) or after a
    # money word (spent/paid/for 300), so quantities like "2 coffees" aren't taken as the price.
    number = r"(\d+(?:,\d{2,3})*(?:\.\d{1,2})?)"  # 1,25,000 (Indian) and 125,000 both work
    amount_match = (
        re.search(r"(?:₹|\brs\.?|\binr)\s*" + number, text_without_date, re.IGNORECASE)
        or re.search(number + r"\s*(?:rs\b|rupees\b|inr\b|/-)", text_without_date, re.IGNORECASE)
        or re.search(r"\b(?:spent|paid|for|of|worth|cost|costs)\s+" + number, text_without_date, re.IGNORECASE)
        or re.search(number, text_without_date)
    )
    amount = float(amount_match.group(1).replace(",", "")) if amount_match else 0.0

    if date_match:
        tx_date = normalize_date(re.sub(r"[/.]", "-", date_match.group(1)))
    elif re.search(r"\byesterday\b", user_text, re.IGNORECASE):
        tx_date = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
    else:
        tx_date = datetime.now().strftime("%d-%m-%Y")

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

    # The "General Merchant" filler isn't a real name, so it must not influence the category
    category = categorize_expense("" if merchant == "General Merchant" else merchant, user_text)

    return {
        "date": tx_date,
        "merchant": merchant,
        "amount": amount,
        "category": category,
        "description": user_text.strip(),
        "source": "Text",
        # Money coming in (refund, salary...) is not an expense: callers must not save it
        "looks_like_income": bool(INCOME_WORDS.search(user_text)),
    }
