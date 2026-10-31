"""Tests for the Milestone 1 data contracts."""

import pytest
from pydantic import ValidationError

from graph.state import TradingState
from schemas import AnalystReport, PortfolioState, RiskResult, TradeProposal


def test_schemas_can_be_created() -> None:
    report = AnalystReport(
        signal="bullish",
        confidence=0.8,
        evidence=["Revenue growth"],
        risks=["Market volatility"],
        summary="Positive outlook.",
    )
    proposal = TradeProposal(
        ticker="AAPL",
        action="BUY",
        position_size=0.1,
        confidence=0.75,
        reason="Strong momentum.",
    )
    portfolio = PortfolioState(cash=10_000.0, total_value=10_000.0, positions={})
    risk = RiskResult(approved=True, violations=[], checked_rules=["position_limit"])

    assert report.signal == "bullish"
    assert proposal.action == "BUY"
    assert portfolio.cash == 10_000.0
    assert risk.approved is True


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_outside_range_is_rejected(confidence: float) -> None:
    with pytest.raises(ValidationError):
        AnalystReport(
            signal="neutral",
            confidence=confidence,
            evidence=[],
            risks=[],
            summary="No clear direction.",
        )


@pytest.mark.parametrize("position_size", [-0.01, 1.01])
def test_position_size_outside_range_is_rejected(position_size: float) -> None:
    with pytest.raises(ValidationError):
        TradeProposal(
            ticker="AAPL",
            action="HOLD",
            position_size=position_size,
            confidence=0.5,
            reason="Waiting for confirmation.",
        )


def test_trading_state_stores_basic_fields() -> None:
    state: TradingState = {
        "ticker": "AAPL",
        "status": "created",
        "run_id": "run-001",
        "event_log": ["State created"],
    }

    assert state["ticker"] == "AAPL"
    assert state["status"] == "created"
    assert state["run_id"] == "run-001"
