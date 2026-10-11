"""The whole app (app.py): login gate, sign up, log in, log out."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

import analytics.analytics  # noqa: F401  (see test_pages.py)
from tools.auth_tool import create_user

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _button(app, label):
    return next(b for b in app.button if b.label == label)


def test_nothing_is_shown_before_logging_in():
    app = AppTest.from_file(APP, default_timeout=60).run()

    assert not app.exception
    assert [t.label for t in app.tabs] == ["🔐 Log in", "✨ Create account"]
    assert not any("Total Spent" in m.value for m in app.markdown)


def test_create_account_logs_in_and_shows_the_dashboard():
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="signup_username").input("asha")
    app.text_input(key="signup_password").input("secret123")
    app.text_input(key="signup_confirm").input("secret123")
    _button(app, "Create account").click().run()

    assert not app.exception
    assert app.session_state["username"] == "asha"
    assert any("Logged in as **asha**" in m.value for m in app.sidebar.markdown)


def test_wrong_password_is_refused():
    create_user("ravi", "secret456")
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="login_username").input("ravi")
    app.text_input(key="login_password").input("not-it")
    _button(app, "Log in").click().run()

    assert "user_id" not in app.session_state
    assert any("Wrong username or password" in e.value for e in app.error)


def test_log_out_goes_back_to_the_login_screen():
    create_user("ravi", "secret456")
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.text_input(key="login_username").input("ravi")
    app.text_input(key="login_password").input("secret456")
    _button(app, "Log in").click().run()
    assert app.session_state["username"] == "ravi"

    _button(app, "Log out").click().run()

    assert "user_id" not in app.session_state
    assert [t.label for t in app.tabs] == ["🔐 Log in", "✨ Create account"]


def _sign_up(app, username, demo=False):
    app.text_input(key="signup_username").input(username)
    app.text_input(key="signup_password").input("secret123")
    app.text_input(key="signup_confirm").input("secret123")
    if demo:
        app.checkbox(key="signup_demo").check()
    _button(app, "Create account").click().run()


def test_brand_new_account_opens_on_budget_setup_with_empty_fields():
    app = AppTest.from_file(APP, default_timeout=60).run()
    _sign_up(app, "newbie")

    assert not app.exception
    assert any("set up your budget" in t.value for t in app.title)
    assert app.number_input(key="profile_income").value is None  # empty, not 0.00
    assert app.number_input(key="setup_budget_Food").value is None
    assert not [c for c in app.checkbox if c.key == "profile_start_fresh"]  # nothing to remove yet
    assert not any("Total Spent" in m.value for m in app.markdown)  # no empty dashboard


def test_account_with_demo_data_opens_on_the_dashboard():
    app = AppTest.from_file(APP, default_timeout=60).run()
    _sign_up(app, "demofan", demo=True)

    assert not app.exception
    assert any(t.value == "SPENDWISE" for t in app.title)
