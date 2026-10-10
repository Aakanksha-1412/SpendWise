"""
Seam: run_agent(question, chat_history=...) — short-term memory of the current chat.
`chat_history` uses the Assistant page's format: [{"role": "user"|"assistant", "content": str, ...}].
"""

from agent.graph import run_agent
from agent.tests.conftest import gemini_asks, gemini_says


def _texts_sent(fake):
    """All message texts Gemini received on its first call."""
    return [message.content for message in fake.received[0]]


def test_earlier_chat_messages_are_sent_to_gemini(fake_gemini):
    fake = fake_gemini([gemini_says("Saved.")])
    history = [
        {"role": "user", "content": "is 500 rs on pizza ok?"},
        {"role": "assistant", "content": "Yes, ₹1,500 will be left. Want me to log it?"},
    ]

    run_agent("yes", chat_history=history)

    sent = _texts_sent(fake)
    assert "is 500 rs on pizza ok?" in sent
    assert "Yes, ₹1,500 will be left. Want me to log it?" in sent
    assert sent[-1] == "yes"


def test_only_the_last_six_earlier_messages_are_sent(fake_gemini):
    fake = fake_gemini([gemini_says("ok")])
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"message {i}"} for i in range(10)]

    run_agent("and transport?", chat_history=history)

    sent = _texts_sent(fake)
    assert [text for text in sent if text.startswith("message")] == [f"message {i}" for i in range(4, 10)]


def test_trace_shows_only_the_steps_for_the_new_question(fake_gemini):
    fake_gemini([
        gemini_asks(("get_budget_status", {"category": "Transport"})),
        gemini_says("Transport has ₹2,450 left."),
    ])
    history = [
        {"role": "user", "content": "how much food budget is left?"},
        {"role": "assistant", "content": "Food has ₹2,000 left."},
    ]

    result = run_agent("and transport?", chat_history=history)

    steps = [step["step"] for step in result["reasoning_trace"]]
    assert steps == ["1. 🧠 Gemini decides", "2. 🔧 Tool runs (Python)", "3. ✍️ Gemini answers"]


def test_current_question_is_not_sent_twice_when_the_page_already_added_it_to_history(fake_gemini):
    fake = fake_gemini([gemini_says("ok")])
    history = [
        {"role": "assistant", "content": "Food has ₹2,000 left."},
        {"role": "user", "content": "and transport?"},  # the page appended the new question already
    ]

    run_agent("and transport?", chat_history=history)

    assert _texts_sent(fake).count("and transport?") == 1
