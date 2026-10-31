"""Tests for mock decision generation and risk-feedback adjustment."""

from nodes.decision_agent import decision_agent_node
from schemas import AnalystReport, PortfolioState, RiskResult


def _report(signal: str) -> AnalystReport:
    return AnalystReport(
        signal=signal,
        confidence=0.7,
        evidence=["Mock evidence"],
        risks=["Mock risk"],
        summary="Mock report.",
    )


def _decision_state(retry_count: int, risk_result: RiskResult | None) -> dict[str, object]:
    return {
        "ticker": "AAPL",
        "fundamental_report": _report("bullish"),
        "technical_report": _report("bearish"),
        "news_report": _report("bullish"),
        "portfolio_state": PortfolioState(cash=50_000, total_value=100_000, positions={}),
        "risk_result": risk_result,
        "risk_retry_count": retry_count,
        "event_log": [],
    }


def test_first_decision_uses_deliberately_oversized_position() -> None:
    update = decision_agent_node(_decision_state(retry_count=0, risk_result=None))
    proposal = update["trade_proposal"]

    assert proposal.position_size == 0.15
    assert proposal.reason == "Two of the three analyst agents are bullish."
    assert update["event_log"] == ["Decision generated with position size 0.15"]


def test_risk_feedback_reduces_the_position_size() -> None:
    prior_risk_result = RiskResult(
        approved=False,
        violations=["MAX_POSITION_EXCEEDED"],
        checked_rules=["MAX_POSITION_SIZE"],
    )
    update = decision_agent_node(_decision_state(retry_count=1, risk_result=prior_risk_result))
    proposal = update["trade_proposal"]

    assert proposal.position_size == 0.08
    assert proposal.reason == "Position size reduced after risk feedback."
    assert update["event_log"] == ["Decision generated with position size 0.08"]
