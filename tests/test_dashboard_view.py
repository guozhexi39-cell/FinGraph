"""Tests for pure dashboard view-model transformations."""

from app.dashboard_view import (
    build_agent_view,
    build_decision_view,
    build_execution_view,
    build_portfolio_view,
    build_risk_view,
    detect_agent_disagreement,
    serializable_state,
)
from schemas import AnalystReport, ExecutionResult, PortfolioState, RiskResult, TradeProposal
from nodes.mock_data import mock_data_node


def _report(signal: str) -> AnalystReport:
    return AnalystReport(
        signal=signal,
        confidence=0.7,
        evidence=["Evidence"],
        risks=["Risk"],
        summary="Summary.",
    )


def test_portfolio_view_formats_position_sizes() -> None:
    view = build_portfolio_view(
        PortfolioState(
            cash=90_000,
            total_value=100_000,
            positions={
                "AAPL": {"quantity": 50, "market_value": 10_000, "position_size": 0.1}
            },
        )
    )

    assert view["cash"] == 90_000
    assert view["position_count"] == 1
    assert view["positions"][0]["Position Size"] == "10%"
    assert build_portfolio_view(None)["positions"] == []


def test_mock_portfolio_quantities_and_totals_reach_dashboard() -> None:
    state = mock_data_node({"ticker": "AAPL", "event_log": []})
    portfolio = state["portfolio_state"]
    view = build_portfolio_view(portfolio)

    assert portfolio["positions"]["AAPL"]["quantity"] == 100
    assert view["positions"] == [
        {
            "Ticker": "AAPL",
            "Quantity": 100,
            "Market Value": 20_000,
            "Position Size": "20%",
        }
    ]
    assert view["cash"] == 80_000
    assert view["total_value"] == 100_000
    holdings_value = sum(row["Market Value"] for row in view["positions"])
    assert view["cash"] + holdings_value == view["total_value"]
    assert portfolio["positions"]["AAPL"]["position_size"] == (
        holdings_value / view["total_value"]
    )


def test_agent_signals_and_disagreement_are_deterministic() -> None:
    bullish = build_agent_view(_report("bullish"))
    neutral = build_agent_view(_report("neutral"))
    bearish = build_agent_view(_report("bearish"))
    mixed_state = {
        "fundamental_report": _report("bullish"),
        "technical_report": _report("neutral"),
        "news_report": _report("bearish"),
    }
    agreed_state = {key: _report("bullish") for key in mixed_state}

    assert [bullish["signal"], neutral["signal"], bearish["signal"]] == [
        "BULLISH",
        "NEUTRAL",
        "BEARISH",
    ]
    assert bullish["confidence_display"] == "70%"
    assert detect_agent_disagreement(mixed_state)["detected"] is True
    assert detect_agent_disagreement(agreed_state)["detected"] is False


def test_decision_risk_and_execution_views_are_converted() -> None:
    proposal = TradeProposal(
        ticker="AAPL",
        action="BUY",
        position_size=0.05,
        entry_price=200,
        stop_loss=190,
        take_profit=220,
        confidence=0.68,
        reason="Evidence supports a small trade.",
    )
    risk_pass = RiskResult(approved=True, violations=[], checked_rules=["MAX_POSITION_SIZE"])
    risk_reject = RiskResult(
        approved=False, violations=["MAX_POSITION_EXCEEDED"], checked_rules=[]
    )
    execution = ExecutionResult(
        order_id="paper-order",
        ticker="AAPL",
        action="BUY",
        quantity=0.01,
        status="accepted",
        paper_trade=True,
    )

    assert build_decision_view(proposal)["position_size_display"] == "5%"
    assert build_risk_view(risk_pass, 0)["approved"] is True
    assert build_risk_view(risk_reject, 1)["violations"] == ["MAX_POSITION_EXCEEDED"]
    assert build_execution_view(execution)["status"] == "accepted"


def test_empty_views_and_raw_state_are_safe_and_redacted() -> None:
    state = {
        "ticker": "AAPL",
        "api_key": "must-not-display",
        "nested": {"secret_key": "must-not-display", "value": 1},
    }

    assert build_agent_view(None) is None
    assert build_decision_view(None) is None
    assert build_risk_view(None, None) is None
    assert build_execution_view(None) is None
    assert serializable_state(state) == {"ticker": "AAPL", "nested": {"value": 1}}
