"""
SpendWise — Upload Expense Page (CSV & Receipt OCR)
===================================================
Owner: Member 4 (Streamlit UI + OCR)

Responsibility:
- Section A: Upload CSV transactions file, auto-categorize rows if needed, preview,
  and bulk-insert into SQLite via `tools/database_tool.py`.
- Section B: Upload Receipt Image (JPG/PNG), invoke `tools/ocr_tool.extract_receipt(image)`
  following the pipeline:
  Image -> OCR -> Extract (Merchant, Date, Items, Tax, Total) -> Categorization -> SQLite.
"""

from datetime import datetime

import streamlit as st
import pandas as pd

from database.database import current_user_id
from tools.ocr_tool import extract_receipt
from tools.categorization_tool import merchant_memory_version
from tools.csv_import_tool import import_rows, read_transactions_csv
from tools.database_tool import add_transaction, expense_already_saved
from utils.helpers import CATEGORIES, expense_date_error, format_inr, is_in_current_month, normalize_date


@st.cache_data(show_spinner="Reading and categorizing transactions...")
def _read_csv(data: bytes, memory_version: int, user_id: int) -> dict:
    """Cleaned CSV rows. Cached, so Streamlit reruns (e.g. clicking Import) don't repeat the
    ChromaDB lookups. `memory_version` and `user_id` are part of the cache key, so newly learned
    merchants are picked up and one user's cached result is never shown to another."""
    return read_transactions_csv(data)


def _receipt_problem(merchant: str, total: float, date: str):
    """What stops this receipt from being saved (plain English), or None."""
    if not merchant.strip():
        return "Please enter the shop name."
    if total <= 0:
        return "Please enter the bill total (more than ₹0)."
    return expense_date_error(date)


def render_upload_page() -> None:
    st.title("📤 Upload Expenses (CSV & Receipt OCR)")
    st.caption("Ingest bank/UPI statement CSVs or extract structured receipt fields using the OCR pipeline.")

    col_csv, col_ocr = st.columns(2, gap="large")

    # =========================================================================
    # SECTION A: UPLOAD CSV
    # =========================================================================
    with col_csv:
        st.markdown("### 📂 A. Upload CSV Statement")
        st.caption("Expected columns: `date`, `merchant`, `amount`, `description` (optional `category`)")

        uploaded_csv = st.file_uploader("Select a CSV file", type=["csv"], key="csv_uploader")

        if uploaded_csv is not None:
            result = _read_csv(uploaded_csv.getvalue(), merchant_memory_version(), current_user_id())
            if result["error"]:
                st.error(result["error"])
            else:
                if result["skipped"]:
                    with st.expander(f"⚠️ {len(result['skipped'])} row(s) will be skipped — see why"):
                        for reason in result["skipped"]:
                            st.markdown(f"- {reason}")
                if result["rows"]:
                    preview = pd.DataFrame(result["rows"])
                    st.markdown(f"**Preview ({len(preview)} expenses ready to import):**")
                    st.dataframe(preview.head(10), width="stretch", hide_index=True)
                    if st.button("Import CSV Transactions to SQLite", type="primary", width="stretch"):
                        outcome = import_rows(result["rows"])
                        message = f"Imported {outcome['imported']} new expenses."
                        if outcome["duplicates"]:
                            message += f" Skipped {outcome['duplicates']} that were already saved in SpendWise."
                        st.success(message)
                else:
                    st.warning("No expenses could be read from this file.")

    # =========================================================================
    # SECTION B: UPLOAD RECEIPT (OCR PIPELINE)
    # =========================================================================
    with col_ocr:
        st.markdown("### 🧾 B. Upload Receipt Image (OCR)")
        st.caption("Pipeline: `Image → OCR → Extract (Merchant, Date, Items, Tax, Total) → Categorization → SQLite`")

        uploaded_image = st.file_uploader(
            "Upload JPG / PNG Receipt",
            type=["jpg", "jpeg", "png"],
            key="receipt_uploader",
        )

        # A different photo (or removing it) clears the previous result, so old fields
        # (e.g. the demo receipt) are never shown under a new, not-yet-read photo.
        current_upload = uploaded_image.file_id if uploaded_image is not None else None
        if st.session_state.get("ocr_upload_id") != current_upload:
            st.session_state["ocr_upload_id"] = current_upload
            st.session_state.pop("ocr_result", None)
            st.session_state.pop("receipt_duplicate_message", None)

        if st.button("Run Demo Receipt Extraction (No File Needed)", width="stretch"):
            st.session_state.pop("receipt_duplicate_message", None)
            st.session_state["ocr_result"] = extract_receipt(None, filename_hint="starbucks_receipt.jpg")

        if uploaded_image is not None:
            st.image(uploaded_image, caption="Uploaded Receipt Image", width=260)
            if st.button("Extract Receipt via OCR Tool", type="primary", width="stretch"):
                st.session_state.pop("receipt_duplicate_message", None)
                st.session_state["ocr_result"] = extract_receipt(
                    uploaded_image, filename_hint=uploaded_image.name
                )

        if "ocr_result" in st.session_state:
            ocr_data = st.session_state["ocr_result"]
            st.markdown("#### Extracted Receipt Fields")
            st.caption(f"Engine: `{ocr_data.get('engine')}`")
            if not ocr_data.get("read_ok", True):
                st.warning("⚠️ This receipt couldn't be read automatically. Please type the merchant, date and total below.")

            # An old bill (e.g. dated March, paid now) must not silently land in another month
            today_str = datetime.now().strftime("%d-%m-%Y")
            old_receipt_date = ocr_data.get("read_ok", True) and not is_in_current_month(ocr_data["date"])

            with st.form("confirm_ocr_form"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    merchant = st.text_input("Merchant", value=ocr_data["merchant"])
                    if old_receipt_date:
                        date_choice = st.radio(
                            "📅 Which date should this expense have?",
                            [f"Today ({today_str})", f"Date on the bill ({ocr_data['date']})"],
                            help="The date printed on the receipt isn't in this month. Choose 'Today' if you're paying it now.",
                        )
                        date_val = today_str if date_choice.startswith("Today") else ocr_data["date"]
                    else:
                        date_val = st.text_input("Date (DD-MM-YYYY)", value=ocr_data["date"])
                    category = st.selectbox(
                        "Auto-Assigned Category",
                        CATEGORIES,
                        index=CATEGORIES.index(ocr_data["category"])
                        if ocr_data["category"] in CATEGORIES
                        else 0,
                    )
                with e_col2:
                    tax_val = st.number_input(
                        "Extracted Tax (₹)", min_value=0.0, value=max(float(ocr_data["tax"]), 0.0), step=5.0
                    )
                    total_val = st.number_input(
                        "Extracted Total (₹)", min_value=0.0, value=max(float(ocr_data["total"]), 0.0), step=10.0
                    )
                    desc_val = st.text_input("Extracted Items", value=ocr_data["description"])

                duplicate_message = st.session_state.get("receipt_duplicate_message")
                if duplicate_message:
                    st.warning(duplicate_message)
                    save_anyway = st.checkbox("This is a different purchase — save it anyway")
                else:
                    save_anyway = False

                if st.form_submit_button("Save Extracted Receipt to SQLite", type="primary"):
                    problem = _receipt_problem(merchant, total_val, date_val)
                    if problem:
                        st.error(f"**This expense was not saved.** {problem}")
                        st.stop()
                    if not save_anyway and expense_already_saved(date_val, merchant, total_val):
                        st.session_state["receipt_duplicate_message"] = (
                            f"You already saved {format_inr(total_val)} at {merchant.strip()} on "
                            f"{normalize_date(date_val)}, so it was not saved again."
                        )
                        st.rerun()
                    st.session_state.pop("receipt_duplicate_message", None)
                    saved = add_transaction(
                        {
                            "date": date_val,
                            "merchant": merchant,
                            "amount": total_val,
                            "category": category,
                            "description": f"{desc_val} (Tax: {format_inr(tax_val)})",
                            "source": "Receipt",
                        }
                    )
                    st.success(
                        f"Saved Receipt Transaction #{saved['id']} ({saved['merchant']} — {format_inr(saved['amount'])}) to SQLite!"
                    )
                    del st.session_state["ocr_result"]


render_upload_page()
