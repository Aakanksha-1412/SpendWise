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

from tools.database_tool import (
    add_transaction,
    delete_transaction,
    get_transaction_months,
    get_transactions,
    update_transaction,
)
from tools.categorization_tool import INCOME_NOT_SAVED, categorize_expense, parse_natural_language_expense
from utils.helpers import CATEGORIES, expense_date_error, format_inr, period_label, to_iso_date


def render_transactions_page() -> None:
    st.title("🧾 Transactions Ledger")
    st.caption("View, filter, and log expenses via natural language or structured entry. Backed by SQLite via `tools/database_tool.py`.")
    # A message from the last save/edit (st.rerun() would otherwise wipe it before it is seen)
    saved_message = st.session_state.pop("tx_saved_message", None)
    if saved_message:
        st.success(saved_message)

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
                        date_problem = expense_date_error(parsed["date"])
                        if parsed["looks_like_income"]:
                            st.warning(INCOME_NOT_SAVED)
                        elif date_problem:
                            st.error(f"**This expense was not saved.** {date_problem}")
                        elif parsed["amount"] > 0:
                            saved = add_transaction(parsed)
                            st.session_state["tx_saved_message"] = (
                                f"Added: {saved['merchant']} — {format_inr(saved['amount'])} "
                                f"under **{saved['category']}** ({saved['date']})"
                            )
                            st.rerun()
                        else:
                            st.warning("I couldn't find an amount. Please include it, for example ₹450.")

        with tab_form:
            with st.form("manual_expense_form", clear_on_submit=True):
                f_cols = st.columns(4)
                with f_cols[0]:
                    tx_date = st.date_input("Date", value=datetime.now(), max_value=datetime.now())  # no future dates
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
                        st.session_state["tx_saved_message"] = (
                            f"Added: {saved['merchant']} — {format_inr(saved['amount'])} "
                            f"under **{saved['category']}** ({saved['date']})"
                        )
                        st.rerun()

    st.divider()

    # -------------------------------------------------------------------------
    # 2. FILTERS (CATEGORY, DATE, MERCHANT)
    # -------------------------------------------------------------------------
    st.markdown("#### Filter Transactions")
    filter_cols = st.columns(4)
    with filter_cols[0]:
        # Default: this month, so the total matches the Home dashboard
        this_month = (datetime.now().month, datetime.now().year)
        months = [this_month] + [m for m in get_transaction_months() if m != this_month]
        month_choice = st.selectbox(
            "Month",
            months + [None],
            format_func=lambda m: "All months" if m is None else period_label(*m),
        )
    with filter_cols[1]:
        selected_category = st.selectbox("Category", ["All"] + CATEGORIES)
    with filter_cols[2]:
        merchant_search = st.text_input("Merchant Search", placeholder="Search Swiggy, Uber, Amazon...")
    with filter_cols[3]:
        date_search = st.text_input("Date Filter (DD-MM-YYYY)", placeholder="e.g., 01-10-2026")

    # -------------------------------------------------------------------------
    # 3. TRANSACTIONS TABLE
    # -------------------------------------------------------------------------
    records = get_transactions(
        category=selected_category,
        merchant_query=merchant_search,
        date_filter=date_search,
        month=month_choice[0] if month_choice else None,
        year=month_choice[1] if month_choice else None,
    )

    if not records:
        st.info("No transactions match the selected filters.")
        return

    records.sort(key=lambda r: (to_iso_date(r["date"]), r["id"]), reverse=True)  # newest date first
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

    period = "all months" if month_choice is None else period_label(*month_choice)
    st.markdown(f"**Showing {len(display_df)} transaction(s)** · Total for {period}: **{format_inr(df['amount'].sum())}**")
    st.dataframe(display_df, width="stretch", hide_index=True)

    render_edit_or_delete(records)


def render_edit_or_delete(records) -> None:
    """Correct or remove one of the expenses listed above."""
    st.markdown("#### ✏️ Edit or delete an expense")
    chosen = st.selectbox(
        "Choose an expense",
        records,
        index=None,
        placeholder="Pick an expense from the list above",
        format_func=lambda r: f"{r['date']} · {r['merchant']} · {format_inr(r['amount'])} · {r['category']}",
        key="tx_to_edit",
    )
    if chosen is None:
        return

    with st.form("edit_expense_form"):
        cols = st.columns(4)
        with cols[0]:
            new_date = st.text_input("Date (DD-MM-YYYY)", value=chosen["date"])
        with cols[1]:
            new_merchant = st.text_input("Merchant", value=chosen["merchant"])
        with cols[2]:
            new_amount = st.number_input("Amount (₹)", min_value=0.0, value=float(chosen["amount"]), step=50.0)
        with cols[3]:
            new_category = st.selectbox(
                "Category", CATEGORIES,
                index=CATEGORIES.index(chosen["category"]) if chosen["category"] in CATEGORIES else len(CATEGORIES) - 1,
            )
        new_description = st.text_input("Description", value=chosen["description"] or "")
        confirm_delete = st.checkbox("Yes, delete this expense permanently")
        save_col, delete_col = st.columns(2)
        with save_col:
            save = st.form_submit_button("Save changes", type="primary", width="stretch")
        with delete_col:
            delete = st.form_submit_button("Delete expense", width="stretch")

    if delete:
        if not confirm_delete:
            st.warning("Tick “Yes, delete this expense permanently” first.")
        elif delete_transaction(chosen["id"]):
            st.session_state["tx_saved_message"] = (
                f"Deleted: {chosen['merchant']} — {format_inr(chosen['amount'])} ({chosen['date']})"
            )
            st.session_state.pop("tx_to_edit", None)
            st.rerun()
    elif save:
        problem = (
            "Please enter the merchant name." if not new_merchant.strip()
            else "Please enter an amount more than ₹0." if new_amount <= 0
            else expense_date_error(new_date)
        )
        if problem:
            st.error(f"**The changes were not saved.** {problem}")
        else:
            update_transaction(chosen["id"], {
                "date": new_date, "merchant": new_merchant.strip(), "amount": new_amount,
                "category": new_category, "description": new_description.strip(),
            })
            st.session_state["tx_saved_message"] = (
                f"Updated: {new_merchant.strip()} — {format_inr(new_amount)} under **{new_category}**"
            )
            st.session_state.pop("tx_to_edit", None)
            st.rerun()


render_transactions_page()
