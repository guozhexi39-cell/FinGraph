"""Tests that real analyst nodes retain their strict partial observations."""

from types import SimpleNamespace

import pytest

from nodes import fundamental_agent, news_agent, technical_agent
from schemas import AnalystReport


class RecordingService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def analyze(self, *, system_prompt: str, ticker: str, data: object) -> AnalystReport:
        self.calls.append(
            {"system_prompt": system_prompt, "ticker": ticker, "data": data}
        )
        return AnalystReport(
            signal="neutral",
            confidence=0.5,
            evidence=["Provided data reviewed."],
            risks=["Inputs are limited."],
            summary="Neutral assessment.",
        )


@pytest.mark.parametrize(
    ("module", "node_name", "data_key", "report_key", "event"),
    [
        (
            fundamental_agent,
            "fundamental_agent_node",
            "fundamental_data",
            "fundamental_report",
            "Fundamental agent completed with real LLM",
        ),
        (
            technical_agent,
            "technical_agent_node",
            "market_data",
            "technical_report",
            "Technical agent completed with real LLM",
        ),
        (
            news_agent,
            "news_agent_node",
            "news_data",
            "news_report",
            "News agent completed with real LLM",
        ),
    ],
)
def test_real_agents_pass_only_their_assigned_data(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    node_name: str,
    data_key: str,
    report_key: str,
    event: str,
) -> None:
    service = RecordingService()
    monkeypatch.setattr(module.settings, "USE_REAL_ANALYST_LLM", True)
    monkeypatch.setattr(module, "get_analyst_llm_service", lambda: service)
    state = {
        "ticker": "AAPL",
        "market_data": {"only": "market"},
        "fundamental_data": {"only": "fundamental"},
        "news_data": [{"only": "news"}],
        "technical_report": "must not be observed",
        "news_report": "must not be observed",
        "trade_proposal": "must not be observed",
        "event_log": [],
    }

    update = getattr(module, node_name)(state)

    assert service.calls == [{
        "system_prompt": service.calls[0]["system_prompt"],
        "ticker": "AAPL",
        "data": state[data_key],
    }]
    assert update[report_key].signal == "neutral"
    assert update["event_log"] == [event]


def test_mock_mode_does_not_create_or_call_the_real_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fundamental_agent.settings, "USE_REAL_ANALYST_LLM", False)
    monkeypatch.setattr(
        fundamental_agent,
        "get_analyst_llm_service",
        lambda: (_ for _ in ()).throw(AssertionError("real service should not run")),
    )

    update = fundamental_agent.fundamental_agent_node(
        {"ticker": "AAPL", "fundamental_data": {}, "event_log": []}
    )

    assert update["fundamental_report"].confidence == 0.82
    assert update["event_log"] == ["Fundamental agent completed"]
