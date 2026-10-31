"""Unit tests for the DeepSeek structured decision service."""

from types import SimpleNamespace

import pytest

from schemas import AnalystReport, PortfolioState, RiskResult
from services.decision_llm_service import (
    DecisionLLMResponseValidationError,
    DecisionLLMService,
)


def _completion(content: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


class FakeCompletions:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _service(
    responses: list[object], max_retries: int = 0
) -> tuple[DecisionLLMService, FakeCompletions]:
    completions = FakeCompletions(responses)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return (
        DecisionLLMService(
            api_key="test-key",
            client=client,
            max_retries=max_retries,
            sleeper=lambda _seconds: None,
        ),
        completions,
    )


def _report(signal: str) -> AnalystReport:
    return AnalystReport(
        signal=signal,
        confidence=0.7,
        evidence=["Evidence"],
        risks=["Risk"],
        summary="Summary.",
    )


def _decision_arguments() -> dict[str, object]:
    return {
        "system_prompt": "Return JSON only.",
        "ticker": "AAPL",
        "fundamental_report": _report("bullish"),
        "technical_report": _report("neutral"),
        "news_report": _report("bearish"),
        "portfolio_state": PortfolioState(
            cash=50_000, total_value=100_000, positions={"AAPL": {"shares": 10}}
        ),
        "risk_result": RiskResult(
            approved=False,
            violations=["MAX_POSITION_EXCEEDED"],
            checked_rules=["MAX_POSITION_SIZE"],
        ),
        "risk_retry_count": 1,
    }


def test_deepseek_json_response_becomes_trade_proposal() -> None:
    service, completions = _service(
        [
            _completion(
                '{"ticker":"AAPL","action":"BUY","position_size":0.05,'
                '"entry_price":210.0,"stop_loss":200.0,"take_profit":230.0,'
                '"confidence":0.68,"reason":"Balanced evidence."}'
            )
        ]
    )

    proposal = service.propose_trade(**_decision_arguments())

    assert proposal.action == "BUY"
    assert proposal.position_size == 0.05
    call = completions.calls[0]
    assert call["response_format"] == {"type": "json_object"}
    assert call["temperature"] == 0.2
    prompt = call["messages"][1]["content"]
    assert "fundamental_report" in prompt
    assert "portfolio_state" in prompt
    assert "MAX_POSITION_EXCEEDED" in prompt
    assert "For HOLD, position_size must be 0.0" in prompt


@pytest.mark.parametrize(
    "content",
    [
        '{"ticker":"AAPL","action":"WAIT","position_size":0.05,"entry_price":null,'
        '"stop_loss":null,"take_profit":null,"confidence":0.5,"reason":"x"}',
        '{"ticker":"AAPL","action":"BUY","position_size":1.1,"entry_price":null,'
        '"stop_loss":null,"take_profit":null,"confidence":0.5,"reason":"x"}',
        '{"ticker":"AAPL","action":"BUY","position_size":0.05,"entry_price":null,'
        '"stop_loss":null,"take_profit":null,"confidence":1.1,"reason":"x"}',
    ],
)
def test_invalid_action_position_size_or_confidence_is_rejected(content: str) -> None:
    service, _ = _service([_completion(content)])

    with pytest.raises(DecisionLLMResponseValidationError, match="TradeProposal"):
        service.propose_trade(**_decision_arguments())


def test_invalid_json_retries_then_raises() -> None:
    service, completions = _service(
        [_completion("not json"), _completion("still not json")], max_retries=1
    )

    with pytest.raises(DecisionLLMResponseValidationError, match="invalid JSON"):
        service.propose_trade(**_decision_arguments())
    assert len(completions.calls) == 2
