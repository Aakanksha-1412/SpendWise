"""
SpendWise — Receipt OCR & Structured Extraction Tool
====================================================
Owner: Team Member 2 (OCR / Receipt Extraction)

Responsibility:
- Processes uploaded receipt images (JPG/PNG) and extracts structured fields:
  Merchant, Date, Line Items, Tax, Total Amount, and Auto-Category.
- Exposes `extract_receipt(image_file) -> dict` for both the Upload UI (`pages/upload.py`)
  and the LangGraph AI Agent (`agent/graph.py`).

INTEGRATION POINTS FOR TEAM MEMBER 2:
1. Local OCR Engine: Uncomment `pytesseract.image_to_string(Image.open(image_file))`
   once Tesseract binary is installed on the host machine.
2. Vision LLM API: Use Gemini Vision (`gemini-2.5-flash`) or OpenAI Vision to parse
   noisy/handwritten receipts directly into JSON schema.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from tools.categorization_tool import categorize_expense


def extract_receipt(image_file: Any, filename_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract structured transaction data from a receipt image.

    Parameters
    ----------
    image_file : UploadedFile | bytes | str
        The receipt image uploaded by the user in Streamlit or passed to the Agent.
    filename_hint : str, optional
        Filename of the uploaded image for contextual demo resolution when OCR binary
        is not yet configured.

    Returns
    -------
    dict
        Structured receipt payload:
        {
            "merchant": str,
            "date": str (DD-MM-YYYY),
            "items": list[{"name": str, "price": float}],
            "tax": float,
            "total": float,
            "category": str,
            "raw_text": str,
            "engine": str
        }
    """
    name = (filename_hint or getattr(image_file, "name", "receipt.jpg")).lower()

    # -------------------------------------------------------------------------
    # TODO (Team Member 2): Replace demo extraction below with live Tesseract
    # or Vision LLM pipeline:
    #
    # from PIL import Image
    # import pytesseract
    # raw_ocr_text = pytesseract.image_to_string(Image.open(image_file))
    # parsed_fields = _parse_ocr_text_with_regex_or_llm(raw_ocr_text)
    # -------------------------------------------------------------------------

    if "amazon" in name or "shoe" in name or "shop" in name:
        merchant = "Amazon Retail India"
        date_str = "02-10-2026"
        items = [
            {"name": "Running Shoes (Size 9)", "price": 1525.42},
        ]
        tax = 274.58
        total = 1800.00
    elif "apollo" in name or "med" in name or "pharm" in name:
        merchant = "Apollo Pharmacy"
        date_str = "06-10-2026"
        items = [
            {"name": "Multivitamin Tablets (30s)", "price": 310.00},
            {"name": "First Aid Antiseptic Kit", "price": 118.57},
        ]
        tax = 51.43
        total = 480.00
    else:
        # Default restaurant receipt demo matching the prompt's example
        merchant = "Starbucks Coffee"
        date_str = datetime.now().strftime("%d-%m-%Y")
        items = [
            {"name": "Java Chip Frappuccino (Tall)", "price": 315.00},
            {"name": "Smoked Chicken Panini", "price": 208.80},
        ]
        tax = 26.20
        total = 550.00

    category = categorize_expense(merchant, " ".join(i["name"] for i in items))

    return {
        "merchant": merchant,
        "date": date_str,
        "items": items,
        "tax": round(tax, 2),
        "total": round(total, 2),
        "category": category,
        "description": ", ".join(item["name"] for item in items),
        "source": "Receipt",
        "engine": "Demo OCR Pipeline (Ready for Tesseract / Vision LLM)",
    }
