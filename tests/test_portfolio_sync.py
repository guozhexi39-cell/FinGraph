"""Offline tests for Alpaca paper portfolio state synchronization."""

from types import SimpleNamespace

import pytest
from langgraph.types import Command

from config import settings
from execution import PaperBrokerError
from graph import builder
from nodes import execution_node, portfolio_sync
from schemas import ExecutionResult, PortfolioState, TradeProposal


class FakeAlpacaClient:
    def __init__(
        self,
        *,
        cash: str = "100000",
        total_value: str = "100000",
        positions: list[object] | None = None,
    ) -> None:
        self.cash = cash
        self.total_value = total_value
        self.positions = positions or []

    def get_account(self) -> object:
        return SimpleNamespace(
            id="paper-account",
            cash=self.cash,
            portfolio_value=self.total_value,
            buying_power="200000",
        )

    def get_all_positions(self) -> list[object]:
        return self.positions


def _real_state() -> dict[str, object]:
    return {
        "ticker": "AAPL",
        "portfolio_state": PortfolioState(cash=1, total_value=1, positions={}),
        "event_log": [],
    }


def test_alpaca_account_and_positions_map_to_portfolio_state() -> None:
    from execution import AlpacaPaperBroker

    client = FakeAlpacaClient(
        cash="90000.5",
        total_value="100000",
        positions=[
            SimpleNamespace(symbol="AAPL", qty="50", market_value="10000"),
            SimpleNamespace(symbol="MSFT", qty="10", market_value="5000"),
        ],
    )

    portfolio = AlpacaPaperBroker(client=client).get_portfolio_state()

    assert portfolio.cash == 90000.5
    assert portfolio.total_value == 100000.0
    assert portfolio.positions == {
        "AAPL": {"quantity": 50.0, "market_value": 10000.0, "position_size": 0.1},
        "MSFT": {"quantity": 10.0, "market_value": 5000.0, "position_size": 0.05},
    }


def test_empty_positions_and_zero_portfolio_value_are_safe() -> None:
    from execution import AlpacaPaperBroker

    empty = AlpacaPaperBroker(client=FakeAlpacaClient(total_value="0")).get_portfolio_state()
    zero_value_position = AlpacaPaperBroker(
        client=FakeAlpacaClient(
            total_value="0",
            positions=[SimpleNamespace(symbol="AAPL", qty="1", market_value="10")],
        )
    ).get_portfolio_state()

    assert empty.positions == {}
    assert zero_value_position.positions["AAPL"]["position_size"] == 0.0


def test_real_sync_updates_state_and_mock_mode_keeps_existing_portfolio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    synced = PortfolioState(
        cash=90000,
        total_value=100000,
        positions={"AAPL": {"quantity": 50.0, "market_value": 10000.0, "position_size": 0.1}},
    )
    monkeypatch.setattr(settings, "USE_REAL_PORTFOLIO_STATE", True)
    monkeypatch.setattr(
        portfolio_sync, "get_paper_broker", lambda: SimpleNamespace(get_portfolio_state=lambda: synced)
    )

    update = portfolio_sync.portfolio_sync_node(_real_state())

    assert update["portfolio_state"] == synced
    assert update["event_log"] == ["Portfolio state synced from Alpaca Paper"]

    monkeypatch.setattr(settings, "USE_REAL_PORTFOLIO_STATE", False)
    monkeypatch.setattr(
        portfolio_sync,
        "get_paper_broker",
        lambda: (_ for _ in ()).throw(AssertionError("broker must not be used")),
    )
    mock_state = _real_state()
    assert portfolio_sync.portfolio_sync_node(mock_state) == {}
    assert mock_state["portfolio_state"].cash == 1


def test_real_sync_failure_never_falls_back_to_mock_portfolio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "USE_REAL_PORTFOLIO_STATE", True)
    monkeypatch.setattr(
        portfolio_sync,
        "get_paper_broker",
        lambda: SimpleNamespace(
            get_portfolio_state=lambda: (_ for _ in ()).throw(PaperBrokerError("down"))
        ),
    )

    with pytest.raises(portfolio_sync.PortfolioSyncError, match="Unable to synchronize"):
        portfolio_sync.portfolio_sync_node(_real_state())


class ClosedLoopBroker:
    """Fake broker whose account state changes only after a submitted fake order."""

    def __init__(self, *, fill_after_execution: bool = True) -> None:
        self.fill_after_execution = fill_after_execution
        self.filled = False
        self.orders: list[dict[str, object]] = []

    def get_portfolio_state(self) -> PortfolioState:
        if self.filled:
            return PortfolioState(
                cash=99000,
                total_value=100000,
                positions={
                    "AAPL": {
                        "quantity": 5.0,
                        "market_value": 1000.0,
                        "position_size": 0.01,
                    }
                },
            )
        return PortfolioState(cash=100000, total_value=100000, positions={})

    def submit_market_order(
        self, *, ticker: str, action: str, quantity: float
    ) -> ExecutionResult:
        self.orders.append({"ticker": ticker, "action": action, "quantity": quantity})
        self.filled = self.fill_after_execution
        return ExecutionResult(
            order_id="closed-loop-order",
            ticker=ticker,
            action=action,
            quantity=quantity,
            status="accepted",
            paper_trade=True,
        )


def test_closed_loop_refreshes_from_broker_and_next_decision_sees_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker = ClosedLoopBroker(fill_after_execution=True)
    seen_portfolios: list[PortfolioState] = []
    original_decision = builder.decision_agent_node

    def observing_decision(state: dict[str, object]) -> dict[str, object]:
        seen_portfolios.append(state["portfolio_state"])
        return original_decision(state)

    monkeypatch.setattr(settings, "USE_REAL_PORTFOLIO_STATE", True)
    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    monkeypatch.setattr(portfolio_sync, "get_paper_broker", lambda: broker)
    monkeypatch.setattr(execution_node, "get_paper_broker", lambda: broker)
    monkeypatch.setattr(builder, "decision_agent_node", observing_decision)
    graph = builder.build_graph()
    first_config = {"configurable": {"thread_id": "closed-loop-first"}}

    graph.invoke({"ticker": "AAPL", "event_log": []}, first_config)
    final_state = graph.invoke(Command(resume={"approved": True}), first_config)

    assert all(portfolio.positions == {} for portfolio in seen_portfolios)
    assert final_state["portfolio_state"].cash == 99000
    assert final_state["portfolio_state"].positions["AAPL"]["position_size"] == 0.01
    assert "Portfolio state refreshed after paper execution" in final_state["event_log"]

    next_config = {"configurable": {"thread_id": "closed-loop-next"}}
    graph.invoke({"ticker": "AAPL", "event_log": []}, next_config)

    assert seen_portfolios[-1].positions["AAPL"]["position_size"] == 0.01


def test_accepted_order_without_position_change_keeps_broker_portfolio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker = ClosedLoopBroker(fill_after_execution=False)
    monkeypatch.setattr(settings, "USE_REAL_PORTFOLIO_STATE", True)
    monkeypatch.setattr(settings, "USE_PAPER_TRADING", True)
    monkeypatch.setattr(portfolio_sync, "get_paper_broker", lambda: broker)
    monkeypatch.setattr(execution_node, "get_paper_broker", lambda: broker)
    graph = builder.build_graph()
    config = {"configurable": {"thread_id": "accepted-not-filled"}}

    graph.invoke({"ticker": "AAPL", "event_log": []}, config)
    final_state = graph.invoke(Command(resume={"approved": True}), config)

    assert final_state["execution_result"].status == "accepted"
    assert final_state["portfolio_state"].cash == 100000
    assert final_state["portfolio_state"].positions == {}


@pytest.mark.parametrize(("approved", "action"), [(False, "BUY"), (True, "HOLD")])
def test_reject_and_hold_never_run_post_execution_refresh(
    monkeypatch: pytest.MonkeyPatch, approved: bool, action: str
) -> None:
    refresh_calls = 0

    def refresh_probe(state: dict[str, object]) -> dict[str, object]:
        nonlocal refresh_calls
        refresh_calls += 1
        return {"event_log": state.get("event_log", [])}

    if action == "HOLD":
        def hold_decision(state: dict[str, object]) -> dict[str, object]:
            return {
                "trade_proposal": TradeProposal(
                    ticker="AAPL", action="HOLD", position_size=0.0,
                    confidence=0.4, reason="No trade."
                ),
                "event_log": [*state.get("event_log", []), "Test HOLD decision"],
            }

        monkeypatch.setattr(builder, "decision_agent_node", hold_decision)

    monkeypatch.setattr(builder, "portfolio_refresh_node", refresh_probe)
    graph = builder.build_graph()
    config = {"configurable": {"thread_id": f"no-refresh-{action}"}}
    state = graph.invoke({"ticker": "AAPL", "event_log": []}, config)
    if action == "BUY":
        graph.invoke(Command(resume={"approved": approved}), config)

    assert refresh_calls == 0
    if action == "HOLD":
        assert "__interrupt__" not in state
