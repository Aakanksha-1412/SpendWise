"""
SpendWise — Transactions Page
=============================
Owner: Member 4 (Streamlit UI) — consumes `tools/database_tool.py` & `tools/categorization_tool.py` (Member 2)

Responsibility:
- Displays the searchable, filterable table of all recorded transactions:
  [Date, Merchant, Amount, Category, Description, Source]
- Provides filters for Category, Date, and Merchant.
- Provides an "Add Expense" section supporting both:
  1. Natural Language Expense Entry (auto-categorized via `categorization_tool.py`)
  2. Structured Form Entry
- Never executes SQL directly; delegates all database operations to `tools/database_tool.py`.
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from tools.database_tool import get_transactions, add_transaction
from tools.categorization_tool import categorize_expense, parse_natural_language_expense
from utils.helpers import CATEGORIES, format_inr
from utils.ui import show_income_alerts


def render_transactions_page() -> None:
    st.title("🧾 Transactions Ledger")
    st.caption("View, filter, and log expenses via natural language or structured entry. Backed by SQLite via `tools/database_tool.py`.")
    show_income_alerts()

    # -------------------------------------------------------------------------
    # 1. ADD EXPENSE SECTION (NATURAL LANGUAGE + MANUAL FORM)
    # -------------------------------------------------------------------------
    with st.expander("➕ Add New Expense (Natural Language or Structured Form)", expanded=True):
        tab_nl, tab_form = st.tabs(["✨ Natural Language Entry", "📝 Structured Expense Form"])

        with tab_nl:
            st.markdown("Enter an expense in plain English—SpendWise will extract the merchant, amount, date, and auto-assign a category.")
            nl_col1, nl_col2 = st.columns([4, 1])
            with nl_col1:
                nl_input = st.text_input(
                    "Natural Language Expense",
                    placeholder="e.g., Spent ₹450 at Swiggy for dinner on 01-10-2026",
                    label_visibility="collapsed",
                )
            with nl_col2:
                if st.button("Parse & Add", type="primary", width="stretch"):
                    if nl_input.strip():
                        parsed = parse_natural_language_expense(nl_input)
                        if parsed["amount"] > 0:
                            saved = add_transaction(parsed)
                            st.success(
                                f"Added: {saved['merchant']} — {format_inr(saved['amount'])} "
                                f"under **{saved['category']}** ({saved['date']})"
                            )
                            st.rerun()
                        else:
                            st.warning("Could not detect an expense amount. Please include a number (e.g., ₹450).")

        with tab_form:
            with st.form("manual_expense_form", clear_on_submit=True):
                f_cols = st.columns(4)
                with f_cols[0]:
                    tx_date = st.date_input("Date", value=datetime.now())
                with f_cols[1]:
                    merchant = st.text_input("Merchant", placeholder="e.g., Swiggy, Uber, Amazon")
                with f_cols[2]:
                    amount = st.number_input("Amount (₹)", min_value=1.0, step=50.0, value=250.0)
                with f_cols[3]:
                    category_choice = st.selectbox("Category (or Auto)", ["Auto-Detect"] + CATEGORIES)

                desc = st.text_input("Description", placeholder="e.g., Dinner with project team")
                submitted = st.form_submit_button("Save Transaction to SQLite", type="primary")

                if submitted:
                    if not merchant.strip():
                        st.error("Please enter a merchant name.")
                    else:
                        final_cat = (
                            categorize_expense(merchant, desc)
                            if category_choice == "Auto-Detect"
                            else category_choice
                        )
                        saved = add_transaction(
                            {
                                "date": tx_date.strftime("%d-%m-%Y"),
                                "merchant": merchant.strip(),
                                "amount": amount,
                                "category": final_cat,
                                "description": desc.strip() or "Manual entry",
                                "source": "Text",
                            }
                        )
                        st.success(
                            f"Recorded {format_inr(saved['amount'])} at {saved['merchant']} ({saved['category']})."
                        )
                        st.rerun()

    st.divider()

    # -------------------------------------------------------------------------
    # 2. FILTERS (CATEGORY, DATE, MERCHANT)
    # -------------------------------------------------------------------------
    st.markdown("#### Filter Transactions")
    filter_cols = st.columns(3)
    with filter_cols[0]:
        selected_category = st.selectbox("Category", ["All"] + CATEGORIES)
    with filter_cols[1]:
        merchant_search = st.text_input("Merchant Search", placeholder="Search Swiggy, Uber, Amazon...")
    with filter_cols[2]:
        date_search = st.text_input("Date Filter (DD-MM-YYYY)", placeholder="e.g., 01-10-2026")

    # -------------------------------------------------------------------------
    # 3. TRANSACTIONS TABLE
    # -------------------------------------------------------------------------
    records = get_transactions(
        category=selected_category,
        merchant_query=merchant_search,
        date_filter=date_search,
    )

    if not records:
        st.info("No transactions match the selected filters.")
        return

    df = pd.DataFrame(records)
    display_df = pd.DataFrame(
        {
            "Date": df["date"],
            "Merchant": df["merchant"],
            "Amount": df["amount"].apply(format_inr),
            "Category": df["category"],
            "Description": df["description"],
            "Source": df["source"],
        }
    )

    st.markdown(f"**Showing {len(display_df)} transaction(s)** · Total Filtered Spend: **{format_inr(df['amount'].sum())}**")
    st.dataframe(display_df, width="stretch", hide_index=True)


render_transactions_page()
