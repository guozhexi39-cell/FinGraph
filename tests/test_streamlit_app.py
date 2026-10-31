"""Headless Streamlit tests that never require a network or graph run on load."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from config import settings
from nodes import execution_node, portfolio_sync
from app.dashboard_runner import DashboardRunner
from app.streamlit_app import reset_dashboard_state
from schemas import ExecutionResult

APP_PATH = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


def test_first_load_renders_dashboard_without_starting_a_run() -> None:
    app_test = AppTest.from_file(APP_PATH).run()

    assert not app_test.exception
    assert app_test.session_state["runner"] is None
    assert app_test.session_state["latest_state"] is None
    assert app_test.session_state["run_status"] == "Idle"
    assert app_test.session_state["active_view"] == "analysis"
    assert app_test.title[0].value == "AAPL analysis"
    assert {f"nav_{view}" for view in VIEWS} <= {button.key for button in app_test.button}
    headings = [element.value for element in app_test.get("header")]
    assert any(label in headings for label in ("Agent analysis", "Analyst perspectives"))
    assert "approve_trade" not in {button.key for button in app_test.button}


def test_widget_rerun_without_run_button_keeps_no_analysis_result() -> None:
    app_test = AppTest.from_file(APP_PATH).run()

    app_test.text_input(key="ticker_input").input(" msft ").run()

    assert not app_test.exception
    assert app_test.session_state["runner"] is None
    assert app_test.session_state["latest_state"] is None


@pytest.mark.parametrize("ticker", ["", "   "])
def test_empty_ticker_error_survives_rerun_without_starting_graph(
    monkeypatch: pytest.MonkeyPatch, ticker: str
) -> None:
    runner_creations: list[str] = []

    def forbidden_runner(*_args, **_kwargs) -> None:
        runner_creations.append("unexpected runner")
        raise AssertionError("An empty ticker must not create a graph runner")

    monkeypatch.setattr(DashboardRunner, "__init__", forbidden_runner)
    app_test = AppTest.from_file(APP_PATH).run()
    app_test.text_input(key="ticker_input").input(ticker).run()

    app_test.button(key="run_analysis").click().run()
    app_test.run()

    assert not app_test.exception
    assert runner_creations == []
    assert app_test.session_state["analysis_error"] == "Ticker must not be empty."
    assert "Ticker must not be empty." in [element.value for element in app_test.error]
    assert app_test.session_state["runner"] is None
    assert app_test.session_state["graph"] is None
    assert app_test.session_state["latest_state"] is None
    assert app_test.session_state["thread_id"] is None
    assert app_test.session_state["run_status"] == "Idle"

    app_test.button(key="reset_dashboard").click().run()
    assert not app_test.exception
    assert app_test.session_state["analysis_error"] is None
    assert not app_test.error


def test_run_stores_interrupt_result_and_later_rerun_does_not_restart_graph() -> None:
    app_test = AppTest.from_file(APP_PATH).run()

    app_test.button(key="run_analysis").click().run()
    first_thread_id = app_test.session_state["thread_id"]
    first_events = list(app_test.session_state["latest_state"]["event_log"])

    app_test.text_input(key="ticker_input").input("MSFT").run()

    assert app_test.session_state["run_status"] == "Awaiting Human Approval"
    assert app_test.session_state["interrupt_payload"] is not None
    assert app_test.session_state["thread_id"] == first_thread_id
    assert app_test.session_state["latest_state"]["event_log"] == first_events
    assert "execution_result" not in app_test.session_state["latest_state"]


def test_reset_dashboard_state_clears_run_data() -> None:
    session = {
        "thread_id": "old-thread",
        "runner": object(),
        "graph": object(),
        "latest_state": {"ticker": "AAPL"},
        "interrupt_payload": {"action": "BUY"},
        "run_status": "Awaiting Human Approval",
        "analysis_error": "Analysis failed: test",
        "selected_ticker": "AAPL",
        "active_view": "holdings",
        "ticker_draft": "MSFT",
        "paper_order_confirmation": True,
    }

    reset_dashboard_state(session)

    assert session["thread_id"] is None
    assert session["runner"] is None
    assert session["latest_state"] is None
    assert session["interrupt_payload"] is None
    assert session["run_status"] == "Idle"
    assert session["analysis_error"] is None
    assert session["active_view"] == "analysis"
    assert session["ticker_draft"] == "AAPL"
    assert session["paper_order_confirmation"] is False


def test_buy_interrupt_shows_controls_and_reject_resumes_without_execution() -> None:
    app_test = AppTest.from_file(APP_PATH).run()
    app_test.button(key="run_analysis").click().run()
    thread_id = app_test.session_state["thread_id"]

    assert app_test.button(key="approve_trade").disabled is False
    assert app_test.button(key="reject_trade").disabled is False
    assert app_test.button(key="run_analysis").disabled is True

    app_test.button(key="reject_trade").click().run()

    state = app_test.session_state["latest_state"]
    assert app_test.session_state["thread_id"] == thread_id
    assert app_test.session_state["run_status"] == "Rejected by Human"
    assert app_test.session_state["interrupt_payload"] is None
    assert "Human rejected trade" in state["event_log"]
    assert "execution_result" not in state
    assert "approve_trade" not in [button.key for button in app_test.button]
    assert "Not executed" in [element.value for element in app_test.info]


def test_approve_resumes_once_and_dashboard_reruns_do_not_repeat_nodes() -> None:
    app_test = AppTest.from_file(APP_PATH).run()
    app_test.button(key="run_analysis").click().run()
    thread_id = app_test.session_state["thread_id"]
    before_events = list(app_test.session_state["latest_state"]["event_log"])

    app_test.button(key="approve_trade").click().run()
    completed = app_test.session_state["latest_state"]
    app_test.run()
    app_test.run()

    assert app_test.session_state["thread_id"] == thread_id
    assert app_test.session_state["interrupt_payload"] is None
    assert app_test.session_state["run_status"] == "Completed"
    for event in (
        "Fundamental agent completed",
        "Technical agent completed",
        "News agent completed",
        "Decision generated with position size 0.15",
        "Decision generated with position size 0.08",
    ):
        assert completed["event_log"].count(event) == before_events.count(event) == 1
        assert app_test.session_state["latest_state"]["event_log"].count(event) == 1
    assert app_test.session_state["latest_state"]["event_log"].count("Human approved trade") == 1
    assert "approve_trade" not in [button.key for button in app_test.button]


def test_hold_and_risk_rejection_never_expose_approval_buttons() -> None:
    app_test = AppTest.from_file(APP_PATH).run()
    app_test.session_state["latest_state"] = {
        "ticker": "AAPL",
        "trade_proposal": {
            "ticker": "AAPL",
            "action": "HOLD",
            "position_size": 0.0,
            "confidence": 0.5,
            "reason": "No trade.",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
        },
        "risk_result": {"approved": True, "violations": [], "checked_rules": []},
        "event_log": [],
    }
    app_test.session_state["interrupt_payload"] = {"action": "HOLD"}
    app_test.run()

    assert "No human approval required for HOLD." in [element.value for element in app_test.info]
    assert "approve_trade" not in [button.key for button in app_test.button]

    app_test.session_state["latest_state"] = {
        "ticker": "AAPL",
        "trade_proposal": {
            "ticker": "AAPL",
            "action": "BUY",
            "position_size": 0.15,
            "confidence": 0.5,
            "reason": "Rejected by risk.",
            "entry_price": 210.0,
            "stop_loss": 200.0,
            "take_profit": 230.0,
        },
        "risk_result": {
            "approved": False,
            "violations": ["MAX_POSITION_EXCEEDED"],
            "checked_rules": [],
        },
        "event_log": [],
    }
    app_test.session_state["interrupt_payload"] = {"action": "BUY", "risk_approved": False}
    app_test.run()

    assert "approve_trade" not in [button.key for button in app_test.button]
    assert any("not eligible" in element.value for element in app_test.info)


def test_paper_approval_requires_confirmation_and_submits_only_once(
    monkeypatch,
) -> None:
    class FakeBroker:
        def __init__(self) -> None:
            self.orders: list[dict[str, object]] = []

        def submit_market_order(
            self, *, ticker: str, action: str, quantity: float
        ) -> ExecutionResult:
            self.orders.append({"ticker": ticker, "action": action, "quantity": quantity})
            return ExecutionResult(
                order_id="paper-order-once",
                ticker=ticker,
                action=action,
                quantity=quantity,
                status="accepted",
                paper_trade=True,
            )

    broker = FakeBroker()
    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    monkeypatch.setattr(execution_node, "get_paper_broker", lambda: broker)
    app_test = AppTest.from_file(APP_PATH).run()
    app_test.button(key="run_analysis").click().run()

    assert app_test.button(key="approve_trade").label == "Approve & Submit Paper Order"
    assert app_test.button(key="approve_trade").disabled is True
    assert "PAPER TRADING ONLY" in [element.value for element in app_test.warning]

    app_test.checkbox(key="_paper_order_confirmation").check().run()
    assert app_test.session_state["paper_order_confirmation"] is True
    runner = app_test.session_state["runner"]
    thread_id = app_test.session_state["thread_id"]
    events = list(app_test.session_state["latest_state"]["event_log"])

    # Streamlit cleans up widget state when its page is hidden. The canonical
    # confirmation must survive that cleanup without starting or resuming a run.
    for view in ("account", "holdings", "execution", "activity", "analysis"):
        _navigate(app_test, view)
        assert app_test.session_state["runner"] is runner
        assert app_test.session_state["thread_id"] == thread_id
        assert app_test.session_state["latest_state"]["event_log"] == events
        assert app_test.session_state["paper_order_confirmation"] is True
        assert broker.orders == []

    assert app_test.checkbox(key="_paper_order_confirmation").value is True
    assert app_test.button(key="approve_trade").disabled is False
    app_test.button(key="approve_trade").click().run()
    app_test.run()
    app_test.run()
    for view in ("execution", "activity", "account", "holdings", "analysis"):
        _navigate(app_test, view)

    assert len(broker.orders) == 1
    assert app_test.session_state["thread_id"] == thread_id
    assert app_test.session_state["run_status"] == "Completed"
    assert app_test.session_state["latest_state"]["event_log"].count("Human approved trade") == 1
    assert app_test.session_state["latest_state"]["execution_result"].order_id == "paper-order-once"
    assert "Order submitted; not filled yet." in [element.value for element in app_test.info]


def test_paper_rejection_never_creates_a_broker(monkeypatch) -> None:
    broker_creations = 0

    def forbidden_broker() -> object:
        nonlocal broker_creations
        broker_creations += 1
        raise AssertionError("Reject must not construct a paper broker")

    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    monkeypatch.setattr(execution_node, "get_paper_broker", forbidden_broker)
    app_test = AppTest.from_file(APP_PATH).run()
    app_test.button(key="run_analysis").click().run()
    app_test.button(key="reject_trade").click().run()

    assert broker_creations == 0
    assert "execution_result" not in app_test.session_state["latest_state"]
    assert app_test.session_state["run_status"] == "Rejected by Human"


VIEWS = ("analysis", "account", "holdings", "execution", "activity")


def _navigate(app_test: AppTest, view: str) -> None:
    app_test.button(key=f"nav_{view}").click().run()
    assert not app_test.exception
    assert app_test.session_state["active_view"] == view


@pytest.mark.parametrize("view", ["account", "holdings"])
def test_account_and_holdings_first_load_never_start_analysis_or_create_broker(
    monkeypatch: pytest.MonkeyPatch, view: str
) -> None:
    calls: list[str] = []

    def forbidden_call(*_args, **_kwargs):
        calls.append("unexpected call")
        raise AssertionError("Opening account information must not call a backend service")

    monkeypatch.setattr(DashboardRunner, "start", forbidden_call)
    monkeypatch.setattr(DashboardRunner, "resume_approval", forbidden_call)
    monkeypatch.setattr(execution_node, "get_paper_broker", forbidden_call)
    monkeypatch.setattr(portfolio_sync, "get_paper_broker", forbidden_call)
    # Even with real integration modes displayed, these pages only render state.
    monkeypatch.setattr(settings, "USE_REAL_PORTFOLIO_STATE", True)
    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    app_test = AppTest.from_file(APP_PATH)
    app_test.session_state["active_view"] = view

    app_test.run()

    assert not app_test.exception
    assert calls == []
    assert app_test.session_state["active_view"] == view
    assert app_test.session_state["runner"] is None
    assert app_test.session_state["latest_state"] is None
    assert app_test.session_state["run_status"] == "Idle"
    assert app_test.title[0].value == {"account": "Account overview", "holdings": "Holdings"}[view]


def test_navigation_preserves_pending_graph_and_never_calls_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_test = AppTest.from_file(APP_PATH).run()
    app_test.button(key="run_analysis").click().run()
    assert not app_test.exception
    runner = app_test.session_state["runner"]
    graph = app_test.session_state["graph"]
    thread_id = app_test.session_state["thread_id"]
    payload = dict(app_test.session_state["interrupt_payload"])
    state = app_test.session_state["latest_state"]
    events = list(state["event_log"])
    calls: list[str] = []

    def forbidden_call(*_args, **_kwargs):
        calls.append("unexpected call")
        raise AssertionError("Navigation must not start/resume a graph or create a broker")

    monkeypatch.setattr(DashboardRunner, "start", forbidden_call)
    monkeypatch.setattr(DashboardRunner, "resume_approval", forbidden_call)
    monkeypatch.setattr(graph, "invoke", forbidden_call)
    monkeypatch.setattr(execution_node, "get_paper_broker", forbidden_call)
    monkeypatch.setattr(portfolio_sync, "get_paper_broker", forbidden_call)

    for view in (*VIEWS[1:], "analysis"):
        _navigate(app_test, view)
        assert app_test.session_state["runner"] is runner
        assert app_test.session_state["graph"] is graph
        assert app_test.session_state["thread_id"] == thread_id
        assert app_test.session_state["latest_state"] is state
        assert app_test.session_state["latest_state"]["event_log"] == events
        assert app_test.session_state["interrupt_payload"] == payload
        assert app_test.session_state["run_status"] == "Awaiting Human Approval"
        assert app_test.session_state["approval_decision"] is None

    assert calls == []
    assert app_test.button(key="run_analysis").disabled is True
    assert app_test.button(key="approve_trade").disabled is False
    assert app_test.button(key="reject_trade").disabled is False


def test_ticker_draft_survives_hidden_widget_cleanup_without_running_analysis() -> None:
    app_test = AppTest.from_file(APP_PATH).run()
    app_test.text_input(key="ticker_input").input(" msft ").run()
    assert app_test.session_state["ticker_draft"] == " msft "

    for view in ("account", "holdings", "execution", "activity", "analysis"):
        _navigate(app_test, view)
        assert app_test.session_state["ticker_draft"] == " msft "
        assert app_test.session_state["runner"] is None
        assert app_test.session_state["latest_state"] is None

    assert app_test.text_input(key="ticker_input").value == " msft "


def test_reset_from_another_view_clears_pending_run_and_saved_widget_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    app_test = AppTest.from_file(APP_PATH).run()
    app_test.text_input(key="ticker_input").input("MSFT").run()
    app_test.button(key="run_analysis").click().run()
    app_test.checkbox(key="_paper_order_confirmation").check().run()
    _navigate(app_test, "holdings")

    app_test.button(key="reset_dashboard").click().run()

    assert not app_test.exception
    assert app_test.session_state["active_view"] == "analysis"
    assert app_test.session_state["runner"] is None
    assert app_test.session_state["graph"] is None
    assert app_test.session_state["thread_id"] is None
    assert app_test.session_state["latest_state"] is None
    assert app_test.session_state["interrupt_payload"] is None
    assert app_test.session_state["approval_decision"] is None
    assert app_test.session_state["run_status"] == "Idle"
    assert app_test.session_state["selected_ticker"] == "AAPL"
    assert app_test.session_state["ticker_draft"] == "AAPL"
    assert app_test.session_state["paper_order_confirmation"] is False
    assert app_test.text_input(key="ticker_input").value == "AAPL"


def test_failed_approval_preserves_uncertain_execution_status_across_views(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    approvals: list[bool] = []

    def failed_resume(self: DashboardRunner, approved: bool):
        approvals.append(approved)
        raise RuntimeError("Portfolio refresh failed after submission.")

    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    monkeypatch.setattr(DashboardRunner, "resume_approval", failed_resume)
    app_test = AppTest.from_file(APP_PATH).run()
    app_test.button(key="run_analysis").click().run()
    app_test.checkbox(key="_paper_order_confirmation").check().run()
    app_test.button(key="approve_trade").click().run()

    assert not app_test.exception
    assert app_test.session_state["run_status"] == "Failed"
    assert app_test.session_state["approval_decision"] is True

    for view in ("account", "execution"):
        _navigate(app_test, view)
        visible_text = "\n".join(
            str(element.value)
            for kind in ("markdown", "caption", "text", "info", "warning", "success", "error")
            for element in app_test.get(kind)
        )
        assert (
            "Execution status unavailable. Review the paper account before retrying."
            in visible_text
        )
        assert "no order submitted" not in visible_text.lower()
        assert "not executed" not in visible_text.lower()
        assert app_test.session_state["run_status"] == "Failed"
        assert app_test.session_state["approval_decision"] is True

    assert approvals == [True]
