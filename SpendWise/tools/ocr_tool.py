"""
SpendWise — Receipt OCR & Structured Extraction Tool
====================================================
Owner: Member 4 (Streamlit UI + OCR)

Responsibility:
- Processes uploaded receipt images (JPG/PNG) and extracts structured fields:
  Merchant, Date, Line Items, Tax, Total Amount, and Auto-Category.
- Exposes `extract_receipt(image_file) -> dict` for both the Upload UI (`pages/upload.py`)
  and the LangGraph AI Agent (`agent/tools_registry.py`).

OCR engines, tried in this order:
1. Gemini Vision  — if GEMINI_API_KEY is set: Gemini reads the photo and returns the fields
                    directly (works with blurry/handwritten receipts; uses 1 Gemini request).
2. Tesseract OCR  — if the Tesseract program is installed (path via TESSERACT_CMD_PATH or PATH):
                    image -> raw text -> simple rules find merchant/date/tax/total.
3. Demo receipt   — ONLY when no image was given (the "Run Demo Receipt" button).
If a real image can't be read, the fields come back EMPTY with read_ok=False — never demo
values, so nobody saves a fake expense by mistake.
"""

import base64
import logging
import re
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.categorization_tool import categorize_expense
from utils.helpers import DEFAULT_GEMINI_MODEL, get_setting, normalize_date

logger = logging.getLogger(__name__)



def extract_receipt(image_file: Any, filename_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract structured transaction data from a receipt image.

    Parameters
    ----------
    image_file : UploadedFile | bytes | str | None
        The receipt image (Streamlit upload, raw bytes, or a file path).
        None = return the demo receipt.
    filename_hint : str, optional
        Filename, used for the image type and to pick a demo receipt.

    Returns
    -------
    dict
        {
            "merchant": str,
            "date": str (DD-MM-YYYY),
            "items": list[{"name": str, "price": float}],
            "tax": float,
            "total": float,
            "category": str,
            "description": str,
            "source": "Receipt",
            "raw_text": str,
            "engine": str,
            "read_ok": bool   (False = a real image could not be read; fields are empty)
        }
    """
    name = (filename_hint or getattr(image_file, "name", "") or "receipt.jpg").lower()
    image_bytes = _read_image_bytes(image_file)

    if image_bytes:
        fields = _extract_with_gemini_vision(image_bytes, name) or _extract_with_tesseract(image_bytes) or _unreadable_receipt()
    else:
        fields = _demo_receipt(name)

    read_ok = fields.get("read_ok", True)
    category = categorize_expense(fields["merchant"], " ".join(item["name"] for item in fields["items"])) if read_ok else "Others"
    return {
        "merchant": fields["merchant"],
        "date": fields["date"],
        "items": fields["items"],
        "tax": round(float(fields["tax"]), 2),
        "total": round(float(fields["total"]), 2),
        "category": category,
        "description": ", ".join(item["name"] for item in fields["items"]) or "Receipt",
        "source": "Receipt",
        "raw_text": fields.get("raw_text", ""),
        "engine": fields["engine"],
        "read_ok": read_ok,
    }


# ==============================================================================
# ENGINE 1: GEMINI VISION
# ==============================================================================
def _extract_with_gemini_vision(image_bytes: bytes, name: str) -> Optional[Dict[str, Any]]:
    api_key = get_setting("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return None
    try:
        from langchain_core.messages import HumanMessage
        from langchain_google_genai import ChatGoogleGenerativeAI
        from pydantic import BaseModel, Field

        class Item(BaseModel):
            name: str
            price: float

        class Receipt(BaseModel):
            merchant: str = Field(description="Shop / restaurant name as printed")
            date: str = Field(description="Purchase date as DD-MM-YYYY; empty if not printed")
            items: List[Item] = Field(default_factory=list)
            tax: float = Field(0.0, description="Total tax (GST/CGST+SGST/VAT); 0 if none")
            total: float = Field(description="Final amount paid, including tax")

        llm = ChatGoogleGenerativeAI(
            model=get_setting("GEMINI_MODEL", DEFAULT_GEMINI_MODEL), google_api_key=api_key, temperature=0
        )
        mime = "image/png" if name.endswith(".png") else "image/jpeg"
        message = HumanMessage(
            content=[
                {"type": "text", "text": "Read this shop receipt and extract the fields. Use only what is printed; amounts in rupees."},
                {"type": "image_url", "image_url": f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"},
            ]
        )
        receipt = llm.with_structured_output(Receipt).invoke([message])
        if receipt is None or receipt.total <= 0:
            return None
        return {
            "merchant": receipt.merchant.strip() or "Unknown Merchant",
            "date": _clean_date(receipt.date),
            "items": [{"name": i.name, "price": float(i.price)} for i in receipt.items],
            "tax": receipt.tax,
            "total": receipt.total,
            "raw_text": "",
            "engine": "Gemini Vision",
        }
    except Exception as exc:  # no internet, quota, unreadable image ...
        logger.warning("Gemini Vision OCR failed: %r", exc)
        return None


# ==============================================================================
# ENGINE 2: TESSERACT OCR + TEXT RULES
# ==============================================================================
def _extract_with_tesseract(image_bytes: bytes) -> Optional[Dict[str, Any]]:
    tesseract_path = get_setting("TESSERACT_CMD_PATH") or shutil.which("tesseract")
    if not tesseract_path:
        return None
    try:
        import io

        import pytesseract
        from PIL import Image

        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        raw_text = pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)))
    except Exception as exc:
        logger.warning("Tesseract OCR failed: %r", exc)
        return None
    fields = parse_receipt_text(raw_text)
    if fields is None:
        return None
    fields["engine"] = "Tesseract OCR"
    return fields


_AMOUNT = r"(?:₹|rs\.?|inr)?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)"


def parse_receipt_text(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Turn raw OCR text into receipt fields with simple rules:
    merchant = first line with letters, date = first date found,
    total = the amount on the last line mentioning "total" (not "sub total"),
    tax = sum of amounts on GST/CGST/SGST/VAT/tax lines.
    Returns None if no total could be found.
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return None

    merchant = next((line for line in lines if re.search(r"[A-Za-z]{3,}", line)), "Unknown Merchant")

    date_pattern = r"\b(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{4}-\d{2}-\d{2})\b"
    date_match = re.search(date_pattern, raw_text)
    receipt_date = _clean_date(date_match.group(1)) if date_match else _clean_date("")

    total = None
    grand_total = None
    tax = 0.0
    items = []
    for line in lines:
        lower = line.lower()
        amounts = re.findall(_AMOUNT, line, re.IGNORECASE)
        is_total_line = "total" in lower or re.search(r"\b(amount\s+(payable|due|paid)|net\s+(amount|payable)|to\s+pay)\b", lower)
        if is_total_line and amounts:
            # "Sub Total", "Total Qty: 3", "Total Items", "Total Savings" are not the amount paid
            if "sub" in lower or re.search(r"total\s*(qty|quantity|items?|savings?|saved|discount)", lower):
                continue
            total = float(amounts[-1].replace(",", ""))
            if re.search(r"\b(grand|net|payable|due|to\s+pay)\b", lower):
                grand_total = total
            continue
        # Dates, times, bill numbers, phone numbers and GSTIN contain digits but aren't prices
        if re.search(date_pattern, line) or re.match(r"(date|time|bill|invoice|order|table|phone|ph|tel|mob|gstin|gst\s*(no|number|reg)|fssai)\b", lower):
            continue
        if not amounts:
            continue
        value = float(amounts[-1].replace(",", ""))
        if re.search(r"\b(gst|cgst|sgst|igst|vat|tax)\b", lower):
            tax += value
        elif "sub" not in lower and re.search(r"[A-Za-z]{3,}", line) and line != merchant:
            items.append({"name": re.sub(_AMOUNT + r"\s*$", "", line, flags=re.IGNORECASE).strip(" .:-x"), "price": value})

    total = grand_total if grand_total is not None else total
    if total is None:
        return None
    return {"merchant": merchant, "date": receipt_date, "items": items, "tax": tax, "total": total, "raw_text": raw_text}


# ==============================================================================
# ENGINE 3: DEMO RECEIPTS (no OCR engine available)
# ==============================================================================
def _demo_receipt(name: str) -> Dict[str, Any]:
    if "amazon" in name or "shoe" in name or "shop" in name:
        merchant, date_str, tax, total = "Amazon Retail India", "02-10-2026", 274.58, 1800.00
        items = [{"name": "Running Shoes (Size 9)", "price": 1525.42}]
    elif "apollo" in name or "med" in name or "pharm" in name:
        merchant, date_str, tax, total = "Apollo Pharmacy", "06-10-2026", 51.43, 480.00
        items = [
            {"name": "Multivitamin Tablets (30s)", "price": 310.00},
            {"name": "First Aid Antiseptic Kit", "price": 118.57},
        ]
    else:
        merchant, date_str, tax, total = "Starbucks Coffee", datetime.now().strftime("%d-%m-%Y"), 26.20, 550.00
        items = [
            {"name": "Java Chip Frappuccino (Tall)", "price": 315.00},
            {"name": "Smoked Chicken Panini", "price": 208.80},
        ]
    return {
        "merchant": merchant,
        "date": date_str,
        "items": items,
        "tax": tax,
        "total": total,
        "raw_text": "",
        "engine": "Demo receipt (no OCR engine available: set GEMINI_API_KEY or install Tesseract)",
    }


def _unreadable_receipt() -> Dict[str, Any]:
    """A real image that no engine could read: empty fields for the user to fill in."""
    return {
        "merchant": "",
        "date": datetime.now().strftime("%d-%m-%Y"),
        "items": [],
        "tax": 0.0,
        "total": 0.0,
        "raw_text": "",
        "engine": "OCR failed: could not read this image (check GEMINI_API_KEY / quota, or install Tesseract)",
        "read_ok": False,
    }


# ==============================================================================
# HELPERS
# ==============================================================================
def _read_image_bytes(image_file: Any) -> Optional[bytes]:
    """Bytes from a Streamlit upload, raw bytes, or a file path (None if nothing usable)."""
    if image_file is None:
        return None
    if isinstance(image_file, (bytes, bytearray)):
        return bytes(image_file)
    if isinstance(image_file, str):
        try:
            with open(image_file, "rb") as handle:
                return handle.read()
        except OSError:
            return None
    if hasattr(image_file, "getvalue"):
        return image_file.getvalue()
    if hasattr(image_file, "read"):
        return image_file.read()
    return None


def _clean_date(value: str) -> str:
    """DD-MM-YYYY, or today's date if the receipt date can't be read."""
    normalized = normalize_date((value or "").replace("/", "-").replace(".", "-"))
    for fmt in ("%d-%m-%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(normalized, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return datetime.now().strftime("%d-%m-%Y")
