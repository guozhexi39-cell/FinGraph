"""English-output contracts for model prompts and validated service responses."""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from nodes.decision_agent import DECISION_SYSTEM_PROMPT
from nodes.fundamental_agent import FUNDAMENTAL_SYSTEM_PROMPT
from nodes.news_agent import NEWS_SYSTEM_PROMPT
from nodes.technical_agent import TECHNICAL_SYSTEM_PROMPT
from services.analyst_llm_service import AnalystLLMService, LLMResponseValidationError
from services.decision_llm_service import (
    DecisionLLMResponseValidationError,
    DecisionLLMService,
)
from services.response_language import contains_chinese


LANGUAGE_DIRECTIVE = "Write all natural-language fields in English only."
HAN_TEXT = "English prefix: \u9700\u8981\u4eba\u5de5\u786e\u8ba4"


class FakeCompletions:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = list(payloads)
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        # Escaped JSON must be checked after decoding, not as raw response text.
        content = json.dumps(self.payloads.pop(0), ensure_ascii=True)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


def _service(
    service_type: type,
    payloads: list[dict[str, Any]],
    *,
    max_retries: int = 0,
) -> tuple[Any, FakeCompletions, list[float]]:
    completions = FakeCompletions(payloads)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    sleeps: list[float] = []
    service = service_type(
        api_key="test-key",
        client=client,
        max_retries=max_retries,
        sleeper=sleeps.append,
    )
    return service, completions, sleeps


def _analyst_payload() -> dict[str, Any]:
    return {
        "signal": "bullish",
        "confidence": 0.73,
        "evidence": ["Revenue growth remains positive."],
        "risks": ["Demand could weaken."],
        "summary": "Growth is positive with demand risk.",
    }


def _decision_payload() -> dict[str, Any]:
    return {
        "ticker": "AAPL",
        "action": "BUY",
        "position_size": 0.08,
        "entry_price": 210.0,
        "stop_loss": 200.0,
        "take_profit": 230.0,
        "confidence": 0.68,
        "reason": "The smaller proposed trade addresses the risk feedback.",
    }


def _invoke(service: Any) -> Any:
    if isinstance(service, AnalystLLMService):
        return service.analyze(
            system_prompt="Return JSON only.",
            ticker="AAPL",
            data={"revenue_growth": 0.08},
        )
    report = _analyst_payload()
    return service.propose_trade(
        system_prompt="Return JSON only.",
        ticker="AAPL",
        fundamental_report=report,
        technical_report=report,
        news_report=report,
        portfolio_state={"cash": 50_000, "total_value": 100_000, "positions": {}},
        risk_result={
            "approved": False,
            "violations": ["MAX_POSITION_EXCEEDED"],
            "checked_rules": ["MAX_POSITION_SIZE"],
        },
        risk_retry_count=1,
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Growth improved.", False),
        ("", False),
        ("Company\u2019s earnings\u2014up 8%\u2026", False),
        ("\u20ac1.2m \u2265 \u00a31m; \u03b1 \U0001f4c8", False),
        ("English plus \u4e2d\u6587.", True),
        ("Extension A: \u3400", True),
        ("Supplementary Han: \U00020000", True),
        ("Compatibility Han: \uf900", True),
    ],
)
def test_han_detection_does_not_reject_other_unicode(text: str, expected: bool) -> None:
    assert contains_chinese(text) is expected


@pytest.mark.parametrize("field", ["summary", "evidence", "risks"])
def test_each_analyst_text_field_rejects_han(field: str) -> None:
    payload = _analyst_payload()
    payload[field] = HAN_TEXT if field == "summary" else ["English item.", HAN_TEXT]
    service, completions, sleeps = _service(AnalystLLMService, [payload])

    with pytest.raises(
        LLMResponseValidationError,
        match=r"^DeepSeek analyst text must be in English only\.$",
    ):
        _invoke(service)

    assert len(completions.calls) == 1
    assert sleeps == []


def test_decision_reason_rejects_han() -> None:
    payload = _decision_payload()
    payload["reason"] = HAN_TEXT
    service, completions, sleeps = _service(DecisionLLMService, [payload])

    with pytest.raises(
        DecisionLLMResponseValidationError,
        match=r"^DeepSeek decision reason must be in English only\.$",
    ):
        _invoke(service)

    assert len(completions.calls) == 1
    assert sleeps == []


@pytest.mark.parametrize("service_type", [AnalystLLMService, DecisionLLMService])
def test_english_unicode_text_is_preserved_and_request_constrains_language(
    service_type: type,
) -> None:
    if service_type is AnalystLLMService:
        payload = _analyst_payload()
        payload.update(
            summary="Company\u2019s growth improved\u2014demand still matters.",
            evidence=["Revenue was \u20ac1.2m; EPS rose 8%\u2026"],
            risks=["Volatility \u2265 the recent baseline."],
        )
    else:
        payload = _decision_payload()
        payload["reason"] = "Company\u2019s demand improved\u2014keep the trade at 8%."
    service, completions, sleeps = _service(service_type, [payload])

    result = _invoke(service)

    assert result.model_dump() == payload
    assert sleeps == []
    assert len(completions.calls) == 1
    messages = completions.calls[0]["messages"]
    assert LANGUAGE_DIRECTIVE in next(
        message["content"] for message in messages if message["role"] == "user"
    )


@pytest.mark.parametrize("service_type", [AnalystLLMService, DecisionLLMService])
def test_language_retry_accepts_english_without_changing_structured_values(
    service_type: type,
) -> None:
    expected = _analyst_payload() if service_type is AnalystLLMService else _decision_payload()
    rejected = dict(expected)
    rejected["summary" if service_type is AnalystLLMService else "reason"] = HAN_TEXT
    service, completions, sleeps = _service(
        service_type, [rejected, expected], max_retries=1
    )

    result = _invoke(service)

    # The language gate must not sanitize, translate, or alter trade parameters.
    assert result.model_dump() == expected
    assert len(completions.calls) == 2
    assert sleeps == [1]
    assert completions.calls[0]["messages"] == completions.calls[1]["messages"]
    for call in completions.calls:
        assert LANGUAGE_DIRECTIVE in call["messages"][1]["content"]


@pytest.mark.parametrize(
    ("service_type", "error_type", "message"),
    [
        (
            AnalystLLMService,
            LLMResponseValidationError,
            "DeepSeek analyst text must be in English only.",
        ),
        (
            DecisionLLMService,
            DecisionLLMResponseValidationError,
            "DeepSeek decision reason must be in English only.",
        ),
    ],
)
def test_repeated_han_exhausts_existing_retry_budget(
    service_type: type, error_type: type[Exception], message: str
) -> None:
    payload = _analyst_payload() if service_type is AnalystLLMService else _decision_payload()
    payload["summary" if service_type is AnalystLLMService else "reason"] = HAN_TEXT
    service, completions, sleeps = _service(
        service_type, [payload, payload], max_retries=1
    )

    with pytest.raises(error_type) as caught:
        _invoke(service)

    assert str(caught.value) == message
    assert len(completions.calls) == 2
    assert sleeps == [1]


@pytest.mark.parametrize(
    "prompt",
    [
        FUNDAMENTAL_SYSTEM_PROMPT,
        TECHNICAL_SYSTEM_PROMPT,
        NEWS_SYSTEM_PROMPT,
        DECISION_SYSTEM_PROMPT,
    ],
    ids=["fundamental", "technical", "news", "decision"],
)
def test_every_node_system_prompt_is_english_and_still_requires_json(prompt: str) -> None:
    assert prompt.strip()
    assert not contains_chinese(prompt)
    assert "JSON" in prompt
