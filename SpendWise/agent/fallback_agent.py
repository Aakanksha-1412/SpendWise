"""
SpendWise — Offline Fallback Agent (Demo Mode, NO LLM)
======================================================
Owner: Member 1 (AI Agent / LangGraph)

Responsibility:
- Backup used by `agent/graph.py` ONLY when Gemini is unavailable
  (no GEMINI_API_KEY, no internet, quota exceeded), so the app never breaks.
- Uses simple keyword rules instead of an LLM:
    Understand Request -> Decide Tool(s) -> Call Tool(s) -> Evaluate -> Generate Response
- This is NOT the real agent. The real agent (Gemini chooses tools) lives in `agent/graph.py`.
  Responses from here are labelled "Demo mode" in the UI.
"""

import re
from typing import Dict, Any, List

from agent.state import AgentState
from tools.ocr_tool import extract_receipt
from tools.categorization_tool import INCOME_NOT_SAVED, parse_natural_language_expense, categorize_expense
from tools.database_tool import add_transaction, get_transactions
from tools.budget_tool import (
    calculate_budget_status,
    get_all_budget_statuses,
    suggest_discretionary_reallocation,
)
from tools.spike_detector import detect_all_category_spikes
from analytics.analytics import check_spend_against_savings, get_summary_metrics
from utils.helpers import CATEGORIES, expense_date_error, format_inr, period_label


# ==============================================================================
# NODE 1: UNDERSTAND REQUEST
# ==============================================================================
def _without_dates(text: str) -> str:
    """The text with dates (01-10-2026, 25/09/2026) removed, so their digits aren't amounts."""
    return re.sub(r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b", " ", text)


def understand_request_node(state: AgentState) -> AgentState:
    """
    Analyze the user's natural language prompt, determine the primary intent,
    and identify any target expense category or proposed amount.
    """
    query = state.get("user_query", "").strip()
    q_lower = query.lower()
    trace = list(state.get("reasoning_trace", []))

    # Detect target category if mentioned
    detected_cat = None
    for cat in CATEGORIES:
        if cat.lower() in q_lower:
            detected_cat = cat
            break
    if not detected_cat:
        inferred = categorize_expense("", query, use_semantic=False)  # a question, not a shop name
        if inferred != "Others":
            detected_cat = inferred

    # Classify intent. Something is only SAVED when the user clearly asks (add/log/spent/
    # paid/bought + a real amount, or an attached receipt) and it isn't a question or a
    # "what if" ("can I afford", "if I spent", "would").
    has_receipt = state.get("uploaded_receipt") is not None
    hypothetical = re.search(r"\b(afford|can i spend|if i|what if|would|should i)\b", q_lower)
    add_verb = re.search(r"\b(add|log|logged|record|spent|paid|bought)\b", q_lower)
    real_amount = re.search(r"\d[\d,]*(?:\.\d+)?(?![\d.,]*\s*%)", _without_dates(q_lower))  # not "20%"
    wants_budget = "budget" in q_lower or "left" in q_lower or "remaining" in q_lower
    is_confirmation = re.fullmatch(r"((yes|yeah|yep|ok|okay|sure|please|do it|log it|add it|save it)[\s.!,]*)+", q_lower)

    if is_confirmation:
        intent = "NEEDS_DETAILS"
    elif "afford" in q_lower or (re.search(r"\b(can|could|should) i\b", q_lower) and real_amount):
        # "can I afford ₹500?", "can i eat icecream of 500", "should I buy shoes for 2000?"
        intent = "AFFORDABILITY_CHECK"
    elif (has_receipt or (add_verb and real_amount)) and not hypothetical:
        intent = "ADD_EXPENSE_AND_CHECK_BUDGET" if wants_budget or has_receipt else "ADD_EXPENSE"
    elif "receipt" in q_lower and not has_receipt and add_verb and not hypothetical:
        intent = "NEEDS_RECEIPT"
    elif "alert" in q_lower or "exceed" in q_lower or "over budget" in q_lower or "why did i" in q_lower:
        intent = "EXPLAIN_BUDGET_ALERT"
    elif "spike" in q_lower or "increased the most" in q_lower or "unusual" in q_lower or "trend" in q_lower:
        intent = "CHECK_SPENDING_SPIKE"
    elif "reduce" in q_lower or "save" in q_lower or "cut" in q_lower or "where can i" in q_lower or "suggest" in q_lower:
        intent = "REDUCE_SPENDING_ADVICE"
    elif detected_cat and any(w in q_lower for w in ["how much", "spent", "left", "remaining", "budget", "status"]):
        intent = "CHECK_CATEGORY_BUDGET"
    else:
        intent = "GENERAL_SUMMARY"

    trace.append(
        {
            "step": "1. Understand Request",
            "detail": f"Classified intent as `{intent}` | Target Category: `{detected_cat or 'All Categories'}`",
        }
    )

    return {
        **state,
        "intent": intent,
        "target_category": detected_cat,
        "reasoning_trace": trace,
    }


# ==============================================================================
# NODE 2: DECIDE REQUIRED TOOL(S)
# ==============================================================================
def decide_required_tool_node(state: AgentState) -> AgentState:
    """
    Select which deterministic SpendWise tools are required to fulfill the request.
    """
    intent = state.get("intent", "GENERAL_SUMMARY")
    has_receipt = state.get("uploaded_receipt") is not None
    trace = list(state.get("reasoning_trace", []))

    tools_to_call: List[str] = []

    if intent in ("NEEDS_DETAILS", "NEEDS_RECEIPT"):
        pass  # nothing to look up: the reply asks the user for what's missing
    elif intent == "ADD_EXPENSE_AND_CHECK_BUDGET":
        if has_receipt:  # only a real attached photo is read; never a made-up demo receipt
            tools_to_call.append("ocr_tool.extract_receipt")
        else:
            tools_to_call.append("categorization_tool.parse_natural_language_expense")
        tools_to_call.extend(
            [
                "database_tool.add_transaction",
                "budget_tool.calculate_budget_status",
            ]
        )
    elif intent == "ADD_EXPENSE":
        tools_to_call.extend(
            [
                "categorization_tool.parse_natural_language_expense",
                "database_tool.add_transaction",
                "budget_tool.calculate_budget_status",
            ]
        )
    elif intent == "CHECK_CATEGORY_BUDGET":
        tools_to_call.extend(
            [
                "budget_tool.calculate_budget_status",
                "spike_detector.detect_spending_spike",
            ]
        )
    elif intent == "AFFORDABILITY_CHECK":
        tools_to_call.extend(
            [
                "budget_tool.calculate_budget_status",
                "budget_tool.suggest_discretionary_reallocation",
            ]
        )
    elif intent == "EXPLAIN_BUDGET_ALERT":
        tools_to_call.extend(
            [
                "budget_tool.get_all_budget_statuses",
                "budget_tool.suggest_discretionary_reallocation",
                "spike_detector.detect_all_category_spikes",
                "database_tool.get_transactions",
            ]
        )
    elif intent == "CHECK_SPENDING_SPIKE":
        tools_to_call.extend(
            [
                "spike_detector.detect_all_category_spikes",
                "budget_tool.get_all_budget_statuses",
            ]
        )
    elif intent == "REDUCE_SPENDING_ADVICE":
        tools_to_call.extend(
            [
                "budget_tool.suggest_discretionary_reallocation",
                "spike_detector.detect_all_category_spikes",
            ]
        )
    else:
        tools_to_call.extend(
            [
                "analytics.get_summary_metrics",
                "budget_tool.suggest_discretionary_reallocation",
                "spike_detector.detect_all_category_spikes",
            ]
        )

    trace.append(
        {
            "step": "2. Decide Required Tool(s)",
            "detail": "Selected tools: " + ", ".join(f"`{t}`" for t in tools_to_call),
        }
    )

    return {
        **state,
        "selected_tools": tools_to_call,
        "reasoning_trace": trace,
    }


# ==============================================================================
# NODE 3: CALL TOOL(S)
# ==============================================================================
def call_tool_node(state: AgentState) -> AgentState:
    """
    Execute the selected deterministic Python tools (OCR, SQLite, Pandas Budget/Spike).
    """
    selected_tools = state.get("selected_tools", [])
    target_cat = state.get("target_category")  # None when the question names no category
    query = state.get("user_query", "")
    trace = list(state.get("reasoning_trace", []))
    outputs: Dict[str, Any] = {}

    for tool_name in selected_tools:
        if tool_name == "ocr_tool.extract_receipt":
            receipt_data = extract_receipt(state.get("uploaded_receipt"), filename_hint=query)
            if not receipt_data.get("read_ok", True):
                outputs["receipt_unreadable"] = True  # save nothing; the reply explains
                continue
            # If user mentioned a specific amount in the prompt, override demo amount
            amt_match = re.search(r"(?:₹|rs\.?|inr\s*)\s*(\d+(?:,\d{2,3})*(?:\.\d{1,2})?)", query, re.IGNORECASE)
            if amt_match:
                receipt_data["total"] = float(amt_match.group(1).replace(",", ""))
            outputs["extracted_receipt"] = receipt_data
            target_cat = receipt_data["category"]

        elif tool_name == "categorization_tool.parse_natural_language_expense":
            parsed_tx = parse_natural_language_expense(query)
            outputs["parsed_expense"] = parsed_tx
            target_cat = parsed_tx["category"]

        elif tool_name == "database_tool.add_transaction":
            tx_source = outputs.get("extracted_receipt") or outputs.get("parsed_expense")
            if tx_source:
                tx_payload = {
                    "date": tx_source.get("date"),
                    "merchant": tx_source.get("merchant", "Restaurant Receipt"),
                    "amount": tx_source.get("total", tx_source.get("amount", 450.0)),
                    "category": tx_source.get("category", target_cat),
                    "description": tx_source.get("description", "Added via SpendWise AI Agent"),
                    "source": tx_source.get("source", "Receipt" if "extracted_receipt" in outputs else "Text"),
                }
                date_problem = expense_date_error(tx_payload["date"] or "")
                if tx_source.get("looks_like_income"):
                    outputs["not_saved_reason"] = INCOME_NOT_SAVED
                elif date_problem:
                    outputs["not_saved_reason"] = f"This expense was not saved. {date_problem}"
                elif tx_payload["amount"] > 0:
                    saved_tx = add_transaction(tx_payload)
                    outputs["saved_transaction"] = saved_tx
                    target_cat = saved_tx["category"]

        elif tool_name == "budget_tool.calculate_budget_status":
            if target_cat:
                outputs["category_budget_status"] = calculate_budget_status(target_cat)

        elif tool_name == "budget_tool.get_all_budget_statuses":
            outputs["all_budget_statuses"] = get_all_budget_statuses()

        elif tool_name == "budget_tool.suggest_discretionary_reallocation":
            outputs["reallocation_plan"] = suggest_discretionary_reallocation()

        elif tool_name == "spike_detector.detect_all_category_spikes":
            outputs["all_spikes"] = detect_all_category_spikes()

        elif tool_name == "spike_detector.detect_spending_spike":
            from tools.spike_detector import detect_spending_spike
            if target_cat:
                outputs["category_spike"] = detect_spending_spike(target_cat)

        elif tool_name == "analytics.get_summary_metrics":
            outputs["summary_metrics"] = get_summary_metrics()

        elif tool_name == "database_tool.get_transactions":
            # Biggest purchases in the asked-about category, else the first over-budget one
            over_cats = outputs.get("reallocation_plan", {}).get("over_budget_categories", [])
            alert_cat = target_cat or (over_cats[0]["category"] if over_cats else None)
            if alert_cat:
                rows = get_transactions(category=alert_cat)
                outputs["top_transactions"] = sorted(rows, key=lambda r: r["amount"], reverse=True)[:3]

    trace.append(
        {
            "step": "3. Call Tool(s)",
            "detail": f"Executed {len(selected_tools)} tool(s) against SQLite & Pandas engine. Computed keys: {list(outputs.keys())}",
        }
    )

    return {
        **state,
        "target_category": target_cat,
        "tool_outputs": outputs,
        "reasoning_trace": trace,
    }


# ==============================================================================
# NODE 4: EVALUATE RESULT
# ==============================================================================
def evaluate_result_node(state: AgentState) -> AgentState:
    """
    Evaluate tool outputs to check budget thresholds, affordability, or anomaly flags
    before generating the final natural-language response.
    """
    intent = state.get("intent", "GENERAL_SUMMARY")
    outputs = state.get("tool_outputs", {})
    query = state.get("user_query", "")
    trace = list(state.get("reasoning_trace", []))
    notes: List[str] = []

    if "category_budget_status" in outputs:
        b_stat = outputs["category_budget_status"]
        notes.append(
            f"Category `{b_stat['category']}` is `{b_stat['status']}` "
            f"(Spent: {format_inr(b_stat['spent'])} / Budget: {format_inr(b_stat['budget'])}, "
            f"Remaining: {format_inr(b_stat['remaining'])}, Utilization: {b_stat['utilization_pct']}%)."
        )

    if intent == "AFFORDABILITY_CHECK":
        b_stat = outputs.get("category_budget_status")  # None when no category was named
        # Prefer a number marked as money ("₹500", "rs 500", "500 rupees") over any other number ("2 pizzas")
        number = r"(\d+(?:,\d{2,3})*(?:\.\d{1,2})?)"  # 2,00,000 (Indian) and 200,000 both work
        text = _without_dates(query)
        amt_match = (
            re.search(r"(?:₹|\brs\.?|\binr)\s*" + number, text, re.IGNORECASE)
            or re.search(number + r"\s*(?:rs\b|rupees\b|inr\b|/-)", text, re.IGNORECASE)
            or re.search(number, text)
        )
        proposed_amt = float(amt_match.group(1).replace(",", "")) if amt_match else None
        savings = check_spend_against_savings(proposed_amt) if proposed_amt else None
        has_budget = bool(b_stat) and b_stat["status"] != "NO BUDGET SET"
        post_remaining = round(b_stat["remaining"] - proposed_amt, 2) if has_budget and proposed_amt else None
        can_afford = (
            proposed_amt is not None
            and (post_remaining is None or post_remaining >= 0)
            and (savings is None or savings["fits"])
        )
        outputs["affordability_eval"] = {
            "proposed_amount": proposed_amt,
            "can_afford": can_afford,
            "remaining_after_expense": post_remaining,
            "savings_message": savings["message"] if savings else None,
            "left_to_spend": savings["left_to_spend"] if savings else None,
            "no_category": b_stat is None,
            "no_budget": bool(b_stat) and not has_budget,
        }
        notes.append(
            f"Affordability evaluation for {format_inr(proposed_amt or 0)}: "
            f"`{'FEASIBLE' if can_afford else 'NOT CONFIRMED'}`."
        )

    trace.append(
        {
            "step": "4. Evaluate Result",
            "detail": " | ".join(notes) if notes else "Evaluated multi-category budget and spike metrics.",
        }
    )

    return {
        **state,
        "evaluation_notes": notes,
        "tool_outputs": outputs,
        "reasoning_trace": trace,
    }


# ==============================================================================
# NODE 5: GENERATE RESPONSE
# ==============================================================================
def generate_response_node(state: AgentState) -> AgentState:
    """
    Build the final response from tool results using fixed templates (no LLM).
    """
    intent = state.get("intent", "GENERAL_SUMMARY")
    outputs = state.get("tool_outputs", {})
    trace = list(state.get("reasoning_trace", []))

    if intent == "NEEDS_DETAILS":
        response = (
            "I'm in demo mode, so I can't see your earlier message and **nothing was saved**. "
            "Please type the whole expense, for example: *Add ₹450 at Swiggy for food*."
        )

    elif intent == "NEEDS_RECEIPT":
        response = (
            "I don't see a receipt photo with your message, so **nothing was saved**. "
            "Please attach the photo, or type the shop and amount, for example: *Add ₹471 at Behrouz Biryani for food*."
        )

    elif intent in ("ADD_EXPENSE_AND_CHECK_BUDGET", "ADD_EXPENSE"):
        saved_tx = outputs.get("saved_transaction")
        b_stat = outputs.get("category_budget_status", {})
        if saved_tx:
            response = (
                f"**Expense Logged & Categorized**\n\n"
                f"- **Merchant:** {saved_tx['merchant']}\n"
                f"- **Amount:** {format_inr(saved_tx['amount'])}\n"
                f"- **Category:** {saved_tx['category']} *(Source: {saved_tx['source']})*\n"
                f"- **Date:** {saved_tx['date']}\n\n"
                f"**Updated {b_stat.get('category', 'Category')} Budget Status:**\n"
                f"- **Monthly Budget:** {format_inr(b_stat.get('budget', 0))}\n"
                f"- **Total Spent:** {format_inr(b_stat.get('spent', 0))} ({b_stat.get('utilization_pct', 0)}%)\n"
                f"- **Remaining Budget:** **{format_inr(b_stat.get('remaining', 0))}** (`{b_stat.get('status', 'OK')}`)"
            )
        elif outputs.get("not_saved_reason"):
            response = f"**{outputs['not_saved_reason']}**"
        elif outputs.get("receipt_unreadable"):
            response = (
                "I couldn't read that receipt photo. Please type the merchant and amount "
                "(for example: *'Add ₹471 at Behrouz Biryani for food'*) or try a clearer photo."
            )
        else:
            response = (
                "Please include the merchant and amount (for example: *'Add ₹550 at Starbucks for food and tell me how much of my food budget is left'*) "
                "or upload a receipt image so I can extract and record it."
            )

    elif intent == "CHECK_CATEGORY_BUDGET":
        b_stat = outputs.get("category_budget_status", {})
        spike = outputs.get("category_spike", {})
        cat_name = b_stat.get("category", "Food")
        response = (
            f"### {cat_name} Spending & Budget Summary ({period_label()})\n\n"
            f"- **Monthly Budget:** {format_inr(b_stat.get('budget', 0))}\n"
            f"- **Actual Spent:** **{format_inr(b_stat.get('spent', 0))}** ({b_stat.get('utilization_pct', 0)}% used)\n"
            f"- **Remaining Budget:** **{format_inr(b_stat.get('remaining', 0))}**\n"
            f"- **Status:** `{b_stat.get('status', 'UNDER BUDGET')}`\n\n"
        )
        if spike.get("spike_detected"):
            response += (
                f"⚠️ **Weekly Spike Notice:** {spike.get('message')} "
                f"Try pacing your {cat_name.lower()} expenses over the remaining days of the month."
            )

    elif intent == "AFFORDABILITY_CHECK":
        b_stat = outputs.get("category_budget_status") or {}
        eval_data = outputs.get("affordability_eval", {})
        proposed = eval_data.get("proposed_amount")
        rem_after = eval_data.get("remaining_after_expense")
        can_afford = eval_data.get("can_afford", False)
        left_to_spend = eval_data.get("left_to_spend")
        fits_savings = (
            f"It fits in the {format_inr(left_to_spend)} you have left to spend this month while keeping your savings goal."
            if left_to_spend is not None
            else ""
        )

        if proposed is None:
            response = "How much is it? Ask like this: *Can I afford ₹2,000 on shopping?*"
        elif eval_data.get("savings_message"):
            response = f"**{eval_data['savings_message']}**"
        elif eval_data.get("no_category"):
            response = (
                f"**Yes, overall.** {fits_savings} "
                f"Tell me the category (for example: *Can I afford {format_inr(proposed)} on shopping?*) "
                "and I'll also check it against that budget."
                if left_to_spend is not None
                else f"Which category is this for? Ask like this: *Can I afford {format_inr(proposed)} on shopping?*"
            )
        elif eval_data.get("no_budget"):
            response = (
                f"You haven't set a {b_stat['category']} budget, so I can't check {format_inr(proposed)} against one. "
                f"{fits_savings} You can set a {b_stat['category']} budget on the 🎯 Budget page."
            )
        elif can_afford:
            response = (
                f"**Yes — You can afford a {format_inr(proposed)} expense in {b_stat.get('category', 'Food')}.**\n\n"
                f"- **Current Remaining {b_stat.get('category')} Budget:** {format_inr(b_stat.get('remaining', 0))}\n"
                f"- **Proposed Expense:** {format_inr(proposed)}\n"
                f"- **Remaining Buffer After Expense:** **{format_inr(rem_after)}**"
            )
        else:
            spare = [
                u["category"]
                for u in outputs.get("reallocation_plan", {}).get("unused_discretionary_categories", [])
                if u["category"] != b_stat.get("category")
            ]
            response = (
                f"**Caution — A {format_inr(proposed)} expense will exceed your {b_stat.get('category')} budget by {format_inr(abs(rem_after))}.**\n\n"
                f"- **Current Remaining {b_stat.get('category')} Budget:** {format_inr(b_stat.get('remaining', 0))}\n"
                + (
                    f"- **Recommendation:** Cut back on discretionary spending in {', '.join(spare[:2])} to make room for this purchase."
                    if spare
                    else "- **Recommendation:** No discretionary budget is left elsewhere — consider postponing this purchase."
                )
            )

    elif intent == "EXPLAIN_BUDGET_ALERT":
        reallocation = outputs.get("reallocation_plan", {})
        over_cats = reallocation.get("over_budget_categories", [])
        spikes = [s for s in outputs.get("all_spikes", []) if s["spike_detected"]]
        asked = state.get("target_category")  # the category the user asked about, if any
        if asked:
            over_cats = [c for c in over_cats if c["category"] == asked]
            spikes = [s for s in spikes if s["category"] == asked]
        if over_cats:
            ob = over_cats[0]
            response = (
                f"### Why You Received a {ob['category']} Budget Alert\n\n"
                f"Your **{ob['category']}** spending has reached **{format_inr(ob['spent'])}** against a monthly budget of **{format_inr(ob['budget'])}**, "
                f"exceeding the limit by **{format_inr(abs(ob['remaining']))}** ({ob['utilization_pct']}% utilization).\n\n"
                f"**Key Contributing Transactions:**\n"
                + "".join(
                    f"- {t['merchant']} (`{format_inr(t['amount'])}` — {t['description'] or t['date']})\n"
                    for t in outputs.get("top_transactions", [])
                )
                + f"\n**💡 SpendWise Reallocation Suggestion:**\n"
                + "\n".join(f"- {s}" for s in reallocation.get("suggestions", []))
            )
        elif spikes:
            sp = spikes[0]
            response = (
                f"### Why You Received a {sp['category']} Spending Alert\n\n"
                f"{sp['message']}\n\n"
                f"- **Previous week:** {format_inr(sp['previous_weekly_spending'])}\n"
                f"- **This week:** **{format_inr(sp['current_weekly_spending'])}**\n\n"
                f"Try pacing your {sp['category'].lower()} expenses over the rest of the month."
            )
        elif asked:
            status = next((s for s in outputs.get("all_budget_statuses", []) if s["category"] == asked), None)
            response = f"There is no {asked} alert right now."
            if status and status["budget"] > 0:
                response += f" You've spent {format_inr(status['spent'])} of your {format_inr(status['budget'])} {asked} budget."
        else:
            response = "You have no budget or spending alerts right now."

    elif intent == "CHECK_SPENDING_SPIKE":
        spikes = outputs.get("all_spikes", [])
        active_spikes = [s for s in spikes if s["spike_detected"]]
        if active_spikes:
            top = active_spikes[0]
            response = (
                f"### Spending Spike Analysis\n\n"
                f"🚨 **{top['category']}** increased the most this week (**{top['change_label']}**).\n\n"
                f"- **Previous Weekly {top['category']} Spending:** {format_inr(top['previous_weekly_spending'])}\n"
                f"- **Current Weekly {top['category']} Spending:** **{format_inr(top['current_weekly_spending'])}**\n"
                f"- **Net Weekly Increase:** +{format_inr(top['increase_amount'])}\n\n"
                f"*{top['message']}*"
            )
        else:
            response = "No abnormal weekly spending spikes (>=35%) were detected across your categories this week."

    elif intent == "REDUCE_SPENDING_ADVICE":
        reallocation = outputs.get("reallocation_plan", {})
        unused = reallocation.get("unused_discretionary_categories", [])
        over_cats = reallocation.get("over_budget_categories", [])
        overrun_total = reallocation.get("total_overrun", 0.0)

        lines = ["### SpendWise Discretionary Reduction & Reallocation Plan\n"]
        if over_cats:
            lines.append(
                f"To offset the **{format_inr(overrun_total)}** budget overrun in **{', '.join(c['category'] for c in over_cats)}**, "
                f"SpendWise recommends trimming discretionary spending in these categories with remaining buffer:\n"
            )
        for u in unused:
            lines.append(
                f"- **{u['category']}**: `{format_inr(u['remaining'])}` remaining of `{format_inr(u['budget'])}` budget "
                f"({u['utilization_pct']}% used) — *Cap non-essential spending here for the rest of the month.*"
            )
        response = "\n".join(lines)

    else:
        summary = outputs.get("summary_metrics", get_summary_metrics())
        reallocation = outputs.get("reallocation_plan", suggest_discretionary_reallocation())
        alert_parts = [
            f"{c['category']} over budget by {format_inr(abs(c['remaining']))}"
            for c in reallocation.get("over_budget_categories", [])
        ] + [
            f"weekly {s['category']} spike {s['change_label']}"
            for s in outputs.get("all_spikes", [])
            if s["spike_detected"]
        ]
        response = (
            f"### SpendWise Financial Overview ({period_label()})\n\n"
            f"- **Total Monthly Budget:** {format_inr(summary['monthly_budget'])}\n"
            f"- **Total Spent So Far:** **{format_inr(summary['total_spent'])}**\n"
            f"- **Remaining Overall Budget:** **{format_inr(summary['remaining_budget'])}**\n"
            f"- **Active Alerts:** {summary['budget_alerts_count']}"
            + (f" ({'; '.join(alert_parts)})" if alert_parts else "")
            + "\n\n"
            f"**Actionable Recommendation:**\n"
            + "\n".join(f"- {s}" for s in reallocation.get("suggestions", []))
        )

    trace.append(
        {
            "step": "5. Generate Response",
            "detail": "Synthesized natural-language financial response from verified tool outputs.",
        }
    )

    return {
        **state,
        "final_response": response,
        "reasoning_trace": trace,
    }


def run_fallback_agent(user_query: str, uploaded_receipt: Any = None) -> Dict[str, Any]:
    """
    Run the keyword pipeline in a fixed order (no LLM, no loop).
    Called by `agent/graph.py -> run_agent()` when Gemini is unavailable.
    Returns the same dict shape as `run_agent()`.
    """
    state: AgentState = {
        "user_query": user_query,
        "uploaded_receipt": uploaded_receipt,
        "reasoning_trace": [],
    }
    for node in (
        understand_request_node,
        decide_required_tool_node,
        call_tool_node,
        evaluate_result_node,
        generate_response_node,
    ):
        state = node(state)
    final_state = state

    return {
        "response": final_state.get("final_response", ""),
        "intent": final_state.get("intent", "GENERAL_SUMMARY"),
        "selected_tools": final_state.get("selected_tools", []),
        "reasoning_trace": final_state.get("reasoning_trace", []),
        "tool_outputs": final_state.get("tool_outputs", {}),
    }
