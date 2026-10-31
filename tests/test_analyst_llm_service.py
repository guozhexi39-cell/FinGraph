"""Unit tests for the DeepSeek structured analyst service."""

from types import SimpleNamespace

import pytest

from services.analyst_llm_service import (
    AnalystLLMService,
    LLMResponseValidationError,
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


def _service(responses: list[object], max_retries: int = 0) -> tuple[AnalystLLMService, FakeCompletions]:
    completions = FakeCompletions(responses)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return (
        AnalystLLMService(
            api_key="test-key",
            client=client,
            max_retries=max_retries,
            sleeper=lambda _seconds: None,
        ),
        completions,
    )


def test_deepseek_json_response_becomes_analyst_report() -> None:
    service, completions = _service(
        [
            _completion(
                '{"signal":"bullish","confidence":0.75,"evidence":["Growth"],'
                '"risks":["Volatility"],"summary":"Positive."}'
            )
        ]
    )

    report = service.analyze(
        system_prompt="Return JSON only.", ticker="AAPL", data={"revenue_growth": 0.1}
    )

    assert report.signal == "bullish"
    assert report.confidence == 0.75
    assert completions.calls[0]["response_format"] == {"type": "json_object"}
    assert "revenue_growth" in completions.calls[0]["messages"][1]["content"]


@pytest.mark.parametrize(
    "content",
    [
        '{"signal":"invalid","confidence":0.5,"evidence":[],"risks":[],"summary":"x"}',
        '{"signal":"bullish","confidence":1.1,"evidence":[],"risks":[],"summary":"x"}',
    ],
)
def test_invalid_signal_or_confidence_is_rejected(content: str) -> None:
    service, _ = _service([_completion(content)])

    with pytest.raises(LLMResponseValidationError):
        service.analyze(system_prompt="Return JSON only.", ticker="AAPL", data={})


def test_invalid_json_retries_then_raises() -> None:
    service, completions = _service([_completion("not json"), _completion("still not json")], 1)

    with pytest.raises(LLMResponseValidationError, match="invalid JSON"):
        service.analyze(system_prompt="Return JSON only.", ticker="AAPL", data={})
    assert len(completions.calls) == 2


def test_empty_content_retries_then_raises() -> None:
    service, completions = _service([_completion(None), _completion("")], 1)

    with pytest.raises(LLMResponseValidationError, match="empty content"):
        service.analyze(system_prompt="Return JSON only.", ticker="AAPL", data={})
    assert len(completions.calls) == 2
