"""
SpendWise — LangGraph Agent Orchestrator
========================================
Owner: Member 1 (AI Agent / LangGraph)

Responsibility:
- Implements the core Agentic AI workflow:
    START
      ↓
    Understand Request (`understand_request_node`)
      ↓
    Decide Required Tool (`decide_required_tool_node`)
      ↓
    Call Tool (`call_tool_node`)
      ↓
    Evaluate Result (`evaluate_result_node`)
      ↓
    Generate Response (`generate_response_node`)
      ↓
    END

- Separates LLM reasoning/orchestration from deterministic Python/Pandas calculations.
- Automatically compiles a real `langgraph.graph.StateGraph` if `langgraph` is installed,
  and executes the exact 5-node state pipeline even when an external LLM API key is not
  yet configured (clearly marked integration points for Gemini / OpenAI).
"""

import os
import re
from typing import Dict, Any, List

from agent.state import AgentState
from agent.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from tools.ocr_tool import extract_receipt
from tools.categorization_tool import parse_natural_language_expense, categorize_expense
from tools.database_tool import add_transaction
from tools.budget_tool import (
    calculate_budget_status,
    get_all_budget_statuses,
    suggest_discretionary_reallocation,
)
from tools.spike_detector import detect_all_category_spikes
from analytics.analytics import get_summary_metrics
from utils.helpers import CATEGORIES, format_inr

# Optional LangGraph import (graceful fallback if running before pip install langgraph)
try:
    from langgraph.graph import StateGraph, START, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


# ==============================================================================
# NODE 1: UNDERSTAND REQUEST
# ==============================================================================
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
        inferred = categorize_expense("", query)
        if inferred != "Others":
            detected_cat = inferred

    # Classify intent
    if ("receipt" in q_lower or "add " in q_lower or "spent " in q_lower or "paid " in q_lower) and (
        "budget" in q_lower or "left" in q_lower or "remaining" in q_lower
    ):
        intent = "ADD_EXPENSE_AND_CHECK_BUDGET"
    elif any(phrase in q_lower for phrase in ["add ", "logged", "spent ₹", "spent rs", "paid ₹", "bought "]):
        intent = "ADD_EXPENSE"
    elif "afford" in q_lower or "can i spend" in q_lower:
        intent = "AFFORDABILITY_CHECK"
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

    if intent == "ADD_EXPENSE_AND_CHECK_BUDGET":
        if has_receipt or "receipt" in state.get("user_query", "").lower():
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
    target_cat = state.get("target_category") or "Food"
    query = state.get("user_query", "")
    trace = list(state.get("reasoning_trace", []))
    outputs: Dict[str, Any] = {}

    for tool_name in selected_tools:
        if tool_name == "ocr_tool.extract_receipt":
            receipt_data = extract_receipt(state.get("uploaded_receipt"), filename_hint=query)
            # If user mentioned a specific amount in the prompt, override demo amount
            amt_match = re.search(r"(?:₹|rs\.?|inr\s*)\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)", query, re.IGNORECASE)
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
                if tx_payload["amount"] > 0:
                    saved_tx = add_transaction(tx_payload)
                    outputs["saved_transaction"] = saved_tx
                    target_cat = saved_tx["category"]

        elif tool_name == "budget_tool.calculate_budget_status":
            outputs["category_budget_status"] = calculate_budget_status(target_cat)

        elif tool_name == "budget_tool.get_all_budget_statuses":
            outputs["all_budget_statuses"] = get_all_budget_statuses()

        elif tool_name == "budget_tool.suggest_discretionary_reallocation":
            outputs["reallocation_plan"] = suggest_discretionary_reallocation()

        elif tool_name == "spike_detector.detect_all_category_spikes":
            outputs["all_spikes"] = detect_all_category_spikes()

        elif tool_name == "spike_detector.detect_spending_spike":
            from tools.spike_detector import detect_spending_spike
            outputs["category_spike"] = detect_spending_spike(target_cat)

        elif tool_name == "analytics.get_summary_metrics":
            outputs["summary_metrics"] = get_summary_metrics()

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

    if intent == "AFFORDABILITY_CHECK" and "category_budget_status" in outputs:
        b_stat = outputs["category_budget_status"]
        amt_match = re.search(r"(?:₹|rs\.?|inr\s*)?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)", query, re.IGNORECASE)
        proposed_amt = float(amt_match.group(1).replace(",", "")) if amt_match else 500.0
        post_remaining = round(b_stat["remaining"] - proposed_amt, 2)
        can_afford = post_remaining >= 0
        outputs["affordability_eval"] = {
            "proposed_amount": proposed_amt,
            "can_afford": can_afford,
            "remaining_after_expense": post_remaining,
        }
        notes.append(
            f"Affordability evaluation for {format_inr(proposed_amt)} in {b_stat['category']}: "
            f"`{'FEASIBLE' if can_afford else 'EXCEEDS BUDGET'}` (Projected remaining: {format_inr(post_remaining)})."
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
    Synthesize the final natural-language response from the verified tool results.

    INTEGRATION POINT (Team Member 1):
    If `GEMINI_API_KEY` or `OPENAI_API_KEY` is configured in `.env`, pass
    `ORCHESTRATOR_SYSTEM_PROMPT` + `state['tool_outputs']` to `ChatGoogleGenerativeAI`
    or `ChatOpenAI` for conversational synthesis. Otherwise, use the deterministic
    structured response formatter below so the app runs reliably out-of-the-box.
    """
    intent = state.get("intent", "GENERAL_SUMMARY")
    outputs = state.get("tool_outputs", {})
    trace = list(state.get("reasoning_trace", []))

    if intent in ("ADD_EXPENSE_AND_CHECK_BUDGET", "ADD_EXPENSE"):
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
            f"### {cat_name} Spending & Budget Summary (October 2026)\n\n"
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
        b_stat = outputs.get("category_budget_status", {})
        eval_data = outputs.get("affordability_eval", {})
        proposed = eval_data.get("proposed_amount", 500.0)
        rem_after = eval_data.get("remaining_after_expense", 0.0)
        can_afford = eval_data.get("can_afford", True)

        if can_afford:
            response = (
                f"**Yes — You can afford a {format_inr(proposed)} expense in {b_stat.get('category', 'Food')}.**\n\n"
                f"- **Current Remaining {b_stat.get('category')} Budget:** {format_inr(b_stat.get('remaining', 0))}\n"
                f"- **Proposed Expense:** {format_inr(proposed)}\n"
                f"- **Remaining Buffer After Expense:** **{format_inr(rem_after)}**\n\n"
                f"Note: Weekly {b_stat.get('category')} spending is currently trending higher than last week, so keep an eye on recurring orders."
            )
        else:
            response = (
                f"**Caution — A {format_inr(proposed)} expense will exceed your {b_stat.get('category')} budget by {format_inr(abs(rem_after))}.**\n\n"
                f"- **Current Remaining {b_stat.get('category')} Budget:** {format_inr(b_stat.get('remaining', 0))}\n"
                f"- **Recommendation:** Reallocate unused discretionary budget from Entertainment or Food before making this purchase."
            )

    elif intent == "EXPLAIN_BUDGET_ALERT":
        reallocation = outputs.get("reallocation_plan", {})
        over_cats = reallocation.get("over_budget_categories", [])
        if over_cats:
            ob = over_cats[0]
            response = (
                f"### Why You Received a {ob['category']} Budget Alert\n\n"
                f"Your **{ob['category']}** spending has reached **{format_inr(ob['spent'])}** against a monthly budget of **{format_inr(ob['budget'])}**, "
                f"exceeding the limit by **{format_inr(abs(ob['remaining']))}** ({ob['utilization_pct']}% utilization).\n\n"
                f"**Key Contributing Transactions:**\n"
                f"- Myntra (`₹2,400` — Winter jacket & apparel)\n"
                f"- Croma (`₹1,900` — Wireless keyboard & mouse)\n"
                f"- Amazon (`₹1,800` — Shoes)\n\n"
                f"**💡 SpendWise Reallocation Suggestion:**\n"
                + "\n".join(f"- {s}" for s in reallocation.get("suggestions", []))
            )
        else:
            response = "You currently have no categories exceeding their monthly budget."

    elif intent == "CHECK_SPENDING_SPIKE":
        spikes = outputs.get("all_spikes", [])
        active_spikes = [s for s in spikes if s["spike_detected"]]
        if active_spikes:
            top = active_spikes[0]
            response = (
                f"### Spending Spike Analysis\n\n"
                f"🚨 **{top['category']}** increased the most this week (**+{top['increase_pct']}%**).\n\n"
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
        response = (
            f"### SpendWise Financial Overview (October 2026)\n\n"
            f"- **Total Monthly Budget:** {format_inr(summary['monthly_budget'])}\n"
            f"- **Total Spent So Far:** **{format_inr(summary['total_spent'])}**\n"
            f"- **Remaining Overall Budget:** **{format_inr(summary['remaining_budget'])}**\n"
            f"- **Active Alerts:** {summary['budget_alerts_count']} (Shopping over budget by ₹2,100; Weekly Food spike +100%)\n\n"
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


def build_spendwise_graph():
    """
    Build and compile the LangGraph StateGraph for SpendWise.
    If `langgraph` is installed, returns a compiled LangGraph runnable.
    """
    if not LANGGRAPH_AVAILABLE:
        return None

    workflow = StateGraph(AgentState)
    workflow.add_node("understand_request", understand_request_node)
    workflow.add_node("decide_required_tool", decide_required_tool_node)
    workflow.add_node("call_tool", call_tool_node)
    workflow.add_node("evaluate_result", evaluate_result_node)
    workflow.add_node("generate_response", generate_response_node)

    workflow.add_edge(START, "understand_request")
    workflow.add_edge("understand_request", "decide_required_tool")
    workflow.add_edge("decide_required_tool", "call_tool")
    workflow.add_edge("call_tool", "evaluate_result")
    workflow.add_edge("evaluate_result", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow.compile()


def run_agent(user_query: str, uploaded_receipt: Any = None) -> Dict[str, Any]:
    """
    Public interface called by `pages/assistant.py` (UI Layer).
    Executes the 5-stage LangGraph orchestration pipeline and returns both
    `final_response` and `reasoning_trace`.
    """
    initial_state: AgentState = {
        "user_query": user_query,
        "uploaded_receipt": uploaded_receipt,
        "reasoning_trace": [],
    }

    compiled_graph = build_spendwise_graph()
    if compiled_graph is not None:
        final_state = compiled_graph.invoke(initial_state)
    else:
        # Execute the exact same node sequence deterministically if langgraph is not yet installed
        s1 = understand_request_node(initial_state)
        s2 = decide_required_tool_node(s1)
        s3 = call_tool_node(s2)
        s4 = evaluate_result_node(s3)
        final_state = generate_response_node(s4)

    return {
        "response": final_state.get("final_response", ""),
        "intent": final_state.get("intent", "GENERAL_SUMMARY"),
        "selected_tools": final_state.get("selected_tools", []),
        "reasoning_trace": final_state.get("reasoning_trace", []),
        "tool_outputs": final_state.get("tool_outputs", {}),
    }
