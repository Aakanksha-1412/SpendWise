"""
SpendWise — AI Assistant Page (`🤖 Ask SpendWise`)
==================================================
Owner: Member 4 (Streamlit UI) — calls `agent/graph.py -> run_agent()` (Member 1)

Responsibility:
- Provides a conversational Agentic AI interface where users can ask questions
  about their spending, check affordability, investigate alerts, or log receipts.
- Invokes `agent/graph.py -> run_agent(user_query)` and renders the LangGraph
  step-by-step tool routing & evaluation trace so the orchestrator flow is transparent.
"""

import streamlit as st
from agent.graph import run_agent

EXAMPLE_PROMPTS = [
    "How much did I spend on food this month?",
    "How much of my food budget is left?",
    "Why did I receive a shopping alert?",
    "Which category increased the most?",
    "Can I afford another ₹500 expense in food?",
    "Show me where I can reduce my spending.",
    "Add this restaurant receipt of ₹450 at Swiggy and tell me how much of my food budget is left.",
]


def render_assistant_page() -> None:
    st.title("🤖 Ask SpendWise")
    st.caption(
        "Agentic Financial Orchestrator · Routes requests through OCR, SQLite, Categorization, "
        "Pandas Budget Status, and Spike Detection tools (`agent/graph.py`)."
    )

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I am **SpendWise**, your autonomous personal financial assistant. "
                    "Ask me about your category budgets, why an alert triggered, weekly spending spikes, "
                    "or ask me to log a new receipt and compute your remaining budget."
                ),
                "trace": [],
            }
        ]

    # -------------------------------------------------------------------------
    # QUICK PROMPT BUTTONS
    # -------------------------------------------------------------------------
    st.markdown("**Try an example query:**")
    btn_cols = st.columns(3)
    triggered_prompt = None
    for idx, prompt_text in enumerate(EXAMPLE_PROMPTS[:6]):
        with btn_cols[idx % 3]:
            if st.button(prompt_text, key=f"sample_q_{idx}", width="stretch"):
                triggered_prompt = prompt_text

    st.divider()

    # -------------------------------------------------------------------------
    # RENDER CHAT MESSAGES & AGENT ORCHESTRATION TRACE
    # -------------------------------------------------------------------------
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("trace"):
                with st.expander("🔍 View LangGraph Agent Tool Routing & Execution Trace"):
                    for step_info in msg["trace"]:
                        st.markdown(f"**{step_info['step']}** — {step_info['detail']}")

    # -------------------------------------------------------------------------
    # OPTIONAL RECEIPT ATTACHMENT (sent with the next message only)
    # -------------------------------------------------------------------------
    st.session_state.setdefault("receipt_upload_version", 0)
    with st.expander("📎 Attach a receipt image to your next message (optional)"):
        receipt = st.file_uploader(
            "Receipt image",
            type=["jpg", "jpeg", "png"],
            key=f"assistant_receipt_{st.session_state['receipt_upload_version']}",
            help="Then ask e.g. 'Add this receipt and tell me how much food budget is left'.",
        )

    # -------------------------------------------------------------------------
    # CHAT INPUT HANDLER
    # -------------------------------------------------------------------------
    user_input = st.chat_input("Ask SpendWise about your expenses, budgets, or receipts...")
    active_query = triggered_prompt or user_input

    if active_query:
        with st.chat_message("user"):
            st.markdown(active_query)
        with st.spinner("SpendWise is thinking..."):
            result = run_agent(active_query, uploaded_receipt=receipt)
        # Save the question and its answer together, so a question is never left without an answer
        st.session_state["chat_history"].extend(
            [
                {"role": "user", "content": active_query, "trace": []},
                {
                    "role": "assistant",
                    "content": result["response"],
                    "trace": result.get("reasoning_trace", []),
                },
            ]
        )
        if receipt is not None:
            st.session_state["receipt_upload_version"] += 1  # clear the uploader after use
        st.rerun()


render_assistant_page()
