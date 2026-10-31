"""Tests for mock data and independent analysis nodes."""

import pytest

from nodes.fundamental_agent import fundamental_agent_node
from nodes.mock_data import mock_data_node
from nodes.news_agent import news_agent_node
from nodes.technical_agent import technical_agent_node
from schemas import AnalystReport


def test_mock_data_node_returns_expected_aapl_data() -> None:
    update = mock_data_node({"ticker": "AAPL", "event_log": ["Run created"]})

    assert update["market_data"] == {
        "current_price": 210.0,
        "price_change_5d": 0.04,
        "volatility": 0.22,
    }
    assert update["fundamental_data"]["debt_level"] == "medium"
    assert update["news_data"][0]["sentiment_hint"] == "positive"
    assert update["portfolio_state"]["positions"]["AAPL"]["quantity"] == 100
    assert update["risk_retry_count"] == 0
    assert update["event_log"] == ["Run created", "Mock data loaded"]


@pytest.fixture
def analysis_state() -> dict[str, object]:
    return {
        "ticker": "AAPL",
        "market_data": {"current_price": 210.0, "volatility": 0.22},
        "fundamental_data": {"revenue_growth": 0.08, "profit_growth": 0.06},
        "news_data": [{"headline": "Demand is strong", "sentiment_hint": "positive"}],
        "event_log": ["Mock data loaded"],
    }


@pytest.mark.parametrize(
    ("node", "report_key", "event_message"),
    [
        (fundamental_agent_node, "fundamental_report", "Fundamental agent completed"),
        (technical_agent_node, "technical_report", "Technical agent completed"),
        (news_agent_node, "news_report", "News agent completed"),
    ],
)
def test_agents_return_valid_reports_and_log_events(
    analysis_state: dict[str, object],
    node: object,
    report_key: str,
    event_message: str,
) -> None:
    update = node(analysis_state)  # type: ignore[operator]
    report = update[report_key]

    assert isinstance(report, AnalystReport)
    assert 0 <= report.confidence <= 1
    assert report.signal in {"bullish", "bearish", "neutral"}
    assert update["event_log"] == ["Mock data loaded", event_message]


def test_all_agents_produce_the_requested_mock_signals(
    analysis_state: dict[str, object],
) -> None:
    assert fundamental_agent_node(analysis_state)["fundamental_report"].signal == "bullish"
    assert technical_agent_node(analysis_state)["technical_report"].signal == "bearish"
    assert news_agent_node(analysis_state)["news_report"].signal == "bullish"
