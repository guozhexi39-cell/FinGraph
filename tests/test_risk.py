"""Tests for risk checks, retry counting, and post-risk routing."""

from graph.routing import route_after_risk
from nodes.risk_engine import CHECKED_RULES, risk_engine_node
from schemas import PortfolioState, RiskResult, TradeProposal


def _state(proposal: TradeProposal | dict[str, object], cash: float = 50_000) -> dict[str, object]:
    return {
        "trade_proposal": proposal,
        "portfolio_state": PortfolioState(cash=cash, total_value=100_000, positions={}),
        "risk_retry_count": 0,
        "event_log": ["Decision generated"],
    }


def _proposal(position_size: float, stop_loss: float | None = 200.0) -> TradeProposal:
    return TradeProposal(
        ticker="AAPL",
        action="BUY",
        position_size=position_size,
        entry_price=210.0,
        stop_loss=stop_loss,
        take_profit=230.0,
        confidence=0.7,
        reason="Test proposal.",
    )


def test_oversized_position_is_rejected_and_increments_retry() -> None:
    update = risk_engine_node(_state(_proposal(0.15)))
    result = update["risk_result"]

    assert result.approved is False
    assert result.violations == ["MAX_POSITION_EXCEEDED"]
    assert result.checked_rules == CHECKED_RULES
    assert update["risk_retry_count"] == 1
    assert update["event_log"][-2:] == [
        "Risk rejected proposal: MAX_POSITION_EXCEEDED",
        "Retrying decision: 1/2",
    ]


def test_valid_eight_percent_position_is_approved() -> None:
    update = risk_engine_node(_state(_proposal(0.08)))

    assert update["risk_result"].approved is True
    assert update["risk_result"].violations == []
    assert update["risk_retry_count"] == 0
    assert update["event_log"][-1] == "Risk approved proposal"


def test_buy_without_stop_loss_is_rejected() -> None:
    update = risk_engine_node(_state(_proposal(0.08, stop_loss=None)))

    assert "STOP_LOSS_REQUIRED" in update["risk_result"].violations
    assert update["risk_result"].approved is False


def test_insufficient_cash_is_rejected() -> None:
    update = risk_engine_node(_state(_proposal(0.08), cash=7_000))

    assert "INSUFFICIENT_CASH" in update["risk_result"].violations
    assert update["risk_result"].approved is False


def test_invalid_position_size_is_reported_for_unvalidated_state_input() -> None:
    proposal = {
        "ticker": "AAPL",
        "action": "BUY",
        "position_size": 1.2,
        "stop_loss": 200.0,
    }
    update = risk_engine_node(_state(proposal))

    assert "INVALID_POSITION_SIZE" in update["risk_result"].violations


def test_route_after_risk_selects_approved_retry_or_abort() -> None:
    approved_state = {
        "risk_result": RiskResult(approved=True, violations=[], checked_rules=[]),
        "trade_proposal": _proposal(0.08),
        "risk_retry_count": 0,
    }
    hold_state = {
        "risk_result": RiskResult(approved=True, violations=[], checked_rules=[]),
        "trade_proposal": TradeProposal(
            ticker="AAPL",
            action="HOLD",
            position_size=0.0,
            confidence=0.5,
            reason="No trade.",
        ),
        "risk_retry_count": 0,
    }
    retry_state = {
        "risk_result": RiskResult(approved=False, violations=["MAX_POSITION_EXCEEDED"], checked_rules=[]),
        "risk_retry_count": 1,
    }
    abort_state = {
        "risk_result": RiskResult(approved=False, violations=["MAX_POSITION_EXCEEDED"], checked_rules=[]),
        "risk_retry_count": 2,
    }

    assert route_after_risk(approved_state) == "human_approval"
    assert route_after_risk(hold_state) == "hold"
    assert route_after_risk(retry_state) == "retry"
    assert route_after_risk(abort_state) == "abort"
