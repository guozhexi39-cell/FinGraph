"""Offline tests for the paper-only Alpaca broker adapter."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from execution.alpaca_paper_broker import (
    PAPER_BASE_URL,
    AlpacaPaperBroker,
    PaperBrokerError,
)
from schemas import ExecutionResult


class FakePaperClient:
    def __init__(self, *, order_status: str = "accepted") -> None:
        self.order_status = order_status
        self.order_requests: list[object] = []

    def get_account(self) -> object:
        return SimpleNamespace(
            id="paper-account-1",
            cash="50000.50",
            portfolio_value="100000.25",
            buying_power="150000.00",
        )

    def get_all_positions(self) -> list[object]:
        return [SimpleNamespace(symbol="AAPL", qty="12.5", market_value="2500.00")]

    def submit_order(self, *, order_data: object) -> object:
        self.order_requests.append(order_data)
        return SimpleNamespace(
            id="paper-order-1",
            symbol=order_data.symbol,
            status=self.order_status,
            submitted_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
            filled_at=None,
            filled_avg_price=None,
        )

    def get_order_by_id(self, order_id: str) -> object:
        return SimpleNamespace(
            id=order_id,
            symbol="AAPL",
            status="filled",
            submitted_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
            filled_at=datetime(2026, 8, 9, 0, 1, tzinfo=timezone.utc),
            filled_avg_price="210.25",
        )


def test_broker_is_constructed_with_fixed_paper_safety_settings() -> None:
    captured: dict[str, object] = {}

    def factory(*args: object, **kwargs: object) -> FakePaperClient:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return FakePaperClient()

    AlpacaPaperBroker(api_key="key", secret_key="secret", client_factory=factory)

    assert captured["kwargs"] == {"paper": True, "url_override": PAPER_BASE_URL}


def test_account_and_positions_are_normalized() -> None:
    broker = AlpacaPaperBroker(client=FakePaperClient())

    assert broker.get_account() == {
        "account_id": "paper-account-1",
        "cash": 50000.5,
        "portfolio_value": 100000.25,
        "buying_power": 150000.0,
        "paper_trade": True,
    }
    assert broker.get_positions() == [
        {"ticker": "AAPL", "quantity": 12.5, "market_value": 2500.0}
    ]


@pytest.mark.parametrize(("action", "expected_side"), [("BUY", "buy"), ("SELL", "sell")])
def test_market_order_is_submitted_and_normalized(
    action: str, expected_side: str
) -> None:
    client = FakePaperClient()
    broker = AlpacaPaperBroker(client=client)

    result = broker.submit_market_order(ticker="aapl", action=action, quantity=1.25)

    request = client.order_requests[0]
    assert request.symbol == "AAPL"
    assert request.qty == 1.25
    assert request.side.value == expected_side
    assert result.model_dump() == {
        "order_id": "paper-order-1",
        "ticker": "AAPL",
        "action": action,
        "quantity": 1.25,
        "status": "accepted",
        "submitted_at": "2026-08-09T00:00:00+00:00",
        "filled_at": None,
        "filled_price": None,
        "paper_trade": True,
    }


def test_rejected_order_is_preserved_in_execution_result() -> None:
    broker = AlpacaPaperBroker(client=FakePaperClient(order_status="rejected"))

    result = broker.submit_market_order(ticker="AAPL", action="BUY", quantity=1)

    assert result.status == "rejected"
    assert result.paper_trade is True


def test_order_status_is_normalized() -> None:
    broker = AlpacaPaperBroker(client=FakePaperClient())

    result = broker.get_order_status("paper-order-2", action="BUY", quantity=2)

    assert result.status == "filled"
    assert result.filled_price == 210.25
    assert result.filled_at == "2026-08-09T00:01:00+00:00"


def test_alpaca_errors_are_not_silently_ignored() -> None:
    class FailingClient(FakePaperClient):
        def submit_order(self, *, order_data: object) -> object:
            raise RuntimeError("network failure")

    broker = AlpacaPaperBroker(client=FailingClient())

    with pytest.raises(PaperBrokerError, match="Unable to submit"):
        broker.submit_market_order(ticker="AAPL", action="BUY", quantity=1)


def test_execution_result_enforces_paper_trade_true() -> None:
    with pytest.raises(ValidationError):
        ExecutionResult(
            order_id="order",
            ticker="AAPL",
            action="BUY",
            quantity=1,
            status="accepted",
            paper_trade=False,
        )
