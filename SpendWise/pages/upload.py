"""
SpendWise — Upload Expense Page (CSV & Receipt OCR)
===================================================
Owner: UI / Frontend Team & Team Member 2 (OCR Integration)

Responsibility:
- Section A: Upload CSV transactions file, auto-categorize rows if needed, preview,
  and bulk-insert into SQLite via `tools/database_tool.py`.
- Section B: Upload Receipt Image (JPG/PNG), invoke `tools/ocr_tool.extract_receipt(image)`
  following the pipeline:
  Image -> OCR -> Extract (Merchant, Date, Items, Tax, Total) -> Categorization -> SQLite.
"""

import streamlit as st
import pandas as pd

from tools.ocr_tool import extract_receipt
from tools.categorization_tool import categorize_expense
from tools.database_tool import add_transaction, bulk_insert_transactions
from utils.helpers import CATEGORIES, format_inr


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
            try:
                csv_df = pd.read_csv(uploaded_csv)
                csv_df.columns = [c.strip().lower() for c in csv_df.columns]

                required = {"date", "merchant", "amount"}
                if not required.issubset(set(csv_df.columns)):
                    st.error(f"CSV must contain at least columns: {required}")
                else:
                    if "description" not in csv_df.columns:
                        csv_df["description"] = "CSV Import"
                    if "category" not in csv_df.columns:
                        csv_df["category"] = csv_df.apply(
                            lambda r: categorize_expense(str(r["merchant"]), str(r["description"])),
                            axis=1,
                        )
                    csv_df["source"] = "CSV"

                    st.markdown(f"**Preview ({len(csv_df)} rows detected):**")
                    st.dataframe(csv_df.head(10), use_container_width=True, hide_index=True)

                    if st.button("Import CSV Transactions to SQLite", type="primary", use_container_width=True):
                        records = csv_df.to_dict(orient="records")
                        count = bulk_insert_transactions(records)
                        st.success(f"Successfully imported {count} transactions into SQLite!")
            except Exception as exc:
                st.error(f"Failed to parse CSV file: {exc}")

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

        if st.button("Run Demo Receipt Extraction (No File Needed)", use_container_width=True):
            st.session_state["ocr_result"] = extract_receipt(None, filename_hint="starbucks_receipt.jpg")

        if uploaded_image is not None:
            st.image(uploaded_image, caption="Uploaded Receipt Image", width=260)
            if st.button("Extract Receipt via OCR Tool", type="primary", use_container_width=True):
                st.session_state["ocr_result"] = extract_receipt(
                    uploaded_image, filename_hint=uploaded_image.name
                )

        if "ocr_result" in st.session_state:
            ocr_data = st.session_state["ocr_result"]
            st.markdown("#### Extracted Receipt Fields")
            st.caption(f"Engine: `{ocr_data.get('engine')}`")

            with st.form("confirm_ocr_form"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    merchant = st.text_input("Merchant", value=ocr_data["merchant"])
                    date_val = st.text_input("Date (DD-MM-YYYY)", value=ocr_data["date"])
                    category = st.selectbox(
                        "Auto-Assigned Category",
                        CATEGORIES,
                        index=CATEGORIES.index(ocr_data["category"])
                        if ocr_data["category"] in CATEGORIES
                        else 0,
                    )
                with e_col2:
                    tax_val = st.number_input("Extracted Tax (₹)", value=float(ocr_data["tax"]), step=5.0)
                    total_val = st.number_input("Extracted Total (₹)", value=float(ocr_data["total"]), step=10.0)
                    desc_val = st.text_input("Extracted Items", value=ocr_data["description"])

                if st.form_submit_button("Save Extracted Receipt to SQLite", type="primary"):
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
