"""Tests for selection and state boundaries of the real decision node."""

import pytest

from nodes import decision_agent
from schemas import AnalystReport, PortfolioState, RiskResult, TradeProposal


def _report(signal: str) -> AnalystReport:
    return AnalystReport(
        signal=signal,
        confidence=0.7,
        evidence=["Evidence"],
        risks=["Risk"],
        summary="Summary.",
    )


def _state(risk_result: RiskResult | None = None) -> dict[str, object]:
    return {
        "ticker": "AAPL",
        "fundamental_report": _report("bullish"),
        "technical_report": _report("neutral"),
        "news_report": _report("bearish"),
        "portfolio_state": PortfolioState(
            cash=50_000, total_value=100_000, positions={"AAPL": {"shares": 10}}
        ),
        "risk_result": risk_result,
        "risk_retry_count": 1 if risk_result else 0,
        "event_log": [],
        "market_data": {"must_not_reach_service": True},
        "fundamental_data": {"must_not_reach_service": True},
        "news_data": [{"must_not_reach_service": True}],
    }


class RecordingDecisionService:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    def propose_trade(self, **kwargs: object) -> TradeProposal:
        self.kwargs = kwargs
        return TradeProposal(
            ticker="AAPL",
            action="HOLD",
            position_size=0.0,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            confidence=0.4,
            reason="Analysts disagree.",
        )


def test_real_decision_node_receives_only_permitted_state(monkeypatch: pytest.MonkeyPatch) -> None:
    service = RecordingDecisionService()
    monkeypatch.setattr(decision_agent.settings, "USE_REAL_DECISION_LLM", True)
    monkeypatch.setattr(decision_agent, "get_decision_llm_service", lambda: service)
    rejected = RiskResult(
        approved=False,
        violations=["MAX_POSITION_EXCEEDED"],
        checked_rules=["MAX_POSITION_SIZE"],
    )

    update = decision_agent.decision_agent_node(_state(rejected))

    assert service.kwargs is not None
    assert set(service.kwargs) == {
        "system_prompt",
        "ticker",
        "fundamental_report",
        "technical_report",
        "news_report",
        "portfolio_state",
        "risk_result",
        "risk_retry_count",
    }
    assert service.kwargs["fundamental_report"].signal == "bullish"
    assert service.kwargs["technical_report"].signal == "neutral"
    assert service.kwargs["news_report"].signal == "bearish"
    assert service.kwargs["portfolio_state"].cash == 50_000
    assert service.kwargs["risk_result"].violations == ["MAX_POSITION_EXCEEDED"]
    assert update["trade_proposal"].action == "HOLD"
    assert update["event_log"] == [
        "Decision generated with real LLM with position size 0.00"
    ]


def test_mock_decision_mode_does_not_call_real_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(decision_agent.settings, "USE_REAL_DECISION_LLM", False)
    monkeypatch.setattr(
        decision_agent,
        "get_decision_llm_service",
        lambda: (_ for _ in ()).throw(AssertionError("real service must not be used")),
    )

    update = decision_agent.decision_agent_node(_state())

    assert update["trade_proposal"].position_size == 0.15
