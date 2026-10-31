"""Tests for approval-gated paper execution and graph integration."""

import pytest
from langgraph.types import Command

from config import settings
from graph import builder
from nodes import execution_node
from schemas import ExecutionResult, PortfolioState, TradeProposal


class FakeBroker:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def submit_market_order(
        self, *, ticker: str, action: str, quantity: float
    ) -> ExecutionResult:
        self.calls.append({"ticker": ticker, "action": action, "quantity": quantity})
        return ExecutionResult(
            order_id="fake-paper-order",
            ticker=ticker,
            action=action,
            quantity=quantity,
            status="accepted",
            paper_trade=True,
        )


def _state(action: str = "BUY", approved: bool | None = True) -> dict[str, object]:
    return {
        "trade_proposal": TradeProposal(
            ticker="AAPL",
            action=action,
            position_size=0.05 if action != "HOLD" else 0.0,
            entry_price=200.0 if action != "HOLD" else None,
            stop_loss=190.0 if action == "BUY" else None,
            take_profit=220.0 if action == "BUY" else None,
            confidence=0.7,
            reason="Test proposal.",
        ),
        "portfolio_state": PortfolioState(cash=50_000, total_value=100_000, positions={}),
        "market_data": {"current_price": 200.0},
        "human_approval": approved,
        "event_log": [],
    }


def test_approved_buy_calculates_fractional_quantity_and_submits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker = FakeBroker()
    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    monkeypatch.setattr(execution_node, "get_paper_broker", lambda: broker)

    update = execution_node.execution_node(_state())

    assert broker.calls == [{"ticker": "AAPL", "action": "BUY", "quantity": 25.0}]
    assert update["execution_result"].paper_trade is True
    assert "Paper order submitted: BUY AAPL 25.0" in update["event_log"]


def test_sell_generates_sell_request(monkeypatch: pytest.MonkeyPatch) -> None:
    broker = FakeBroker()
    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    monkeypatch.setattr(execution_node, "get_paper_broker", lambda: broker)

    execution_node.execution_node(_state(action="SELL"))

    assert broker.calls == [{"ticker": "AAPL", "action": "SELL", "quantity": 25.0}]


@pytest.mark.parametrize(
    ("action", "approved", "event"),
    [
        ("BUY", False, "Execution skipped without human approval"),
        ("HOLD", True, "Execution skipped for HOLD"),
    ],
)
def test_rejected_or_hold_proposal_never_calls_broker(
    monkeypatch: pytest.MonkeyPatch, action: str, approved: bool, event: str
) -> None:
    broker = FakeBroker()
    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    monkeypatch.setattr(execution_node, "get_paper_broker", lambda: broker)

    update = execution_node.execution_node(_state(action=action, approved=approved))

    assert broker.calls == []
    assert update["event_log"][-1] == event


def test_disabled_paper_trading_never_constructs_a_broker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "USE_PAPER_TRADING", False)
    monkeypatch.setattr(
        execution_node,
        "get_paper_broker",
        lambda: (_ for _ in ()).throw(AssertionError("broker must not be constructed")),
    )

    update = execution_node.execution_node(_state())

    assert update["event_log"][-1] == "Paper trading disabled; no order submitted"


def test_graph_executes_only_after_approve_and_not_after_reject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker = FakeBroker()
    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    monkeypatch.setattr(execution_node, "get_paper_broker", lambda: broker)
    graph = builder.build_graph()

    approved_config = {"configurable": {"thread_id": "paper-approved"}}
    graph.invoke({"ticker": "AAPL", "event_log": []}, approved_config)
    approved_state = graph.invoke(Command(resume={"approved": True}), approved_config)

    rejected_config = {"configurable": {"thread_id": "paper-rejected"}}
    graph.invoke({"ticker": "AAPL", "event_log": []}, rejected_config)
    rejected_state = graph.invoke(Command(resume={"approved": False}), rejected_config)

    assert approved_state["execution_result"].order_id == "fake-paper-order"
    assert rejected_state.get("execution_result") is None
    assert len(broker.calls) == 1
    assert "Human rejected trade" in rejected_state["event_log"]
