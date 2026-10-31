"""Shared DeepSeek service for schema-validated trade proposals."""

import json
import os
from time import sleep
from typing import Any, Callable

from openai import OpenAI
from pydantic import ValidationError

from config import settings
from schemas import TradeProposal
from services.response_language import contains_chinese

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
Sleeper = Callable[[float], None]


class DecisionLLMServiceError(Exception):
    """Raised when the DeepSeek decision service cannot complete a request."""


class DecisionLLMConfigurationError(DecisionLLMServiceError):
    """Raised when the required DeepSeek configuration is absent."""


class DecisionLLMResponseValidationError(DecisionLLMServiceError):
    """Raised when model output is empty, non-JSON, or schema-invalid."""


class DecisionLLMService:
    """Generate a validated trade proposal from the supplied decision context."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_retries: int | None = None,
        timeout: float | None = None,
        client: Any | None = None,
        sleeper: Sleeper = sleep,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("DEEPSEEK_API_KEY")
        self._model = model if model is not None else settings.DEEPSEEK_MODEL
        self._temperature = (
            temperature if temperature is not None else settings.DECISION_LLM_TEMPERATURE
        )
        self._max_retries = (
            max_retries if max_retries is not None else settings.DECISION_LLM_MAX_RETRIES
        )
        self._timeout = timeout if timeout is not None else settings.DECISION_LLM_TIMEOUT
        if self._max_retries < 0:
            raise ValueError("max_retries must not be negative.")
        if client is None:
            if not self._api_key:
                raise DecisionLLMConfigurationError("DEEPSEEK_API_KEY must be configured.")
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=DEEPSEEK_BASE_URL,
                timeout=self._timeout,
            )
        else:
            self._client = client
        self._sleeper = sleeper

    def propose_trade(
        self,
        *,
        system_prompt: str,
        ticker: str,
        fundamental_report: Any,
        technical_report: Any,
        news_report: Any,
        portfolio_state: Any,
        risk_result: Any | None,
        risk_retry_count: int,
    ) -> TradeProposal:
        """Request a decision from only the permitted structured state fields."""
        context = {
            "ticker": ticker,
            "fundamental_report": _as_json_data(fundamental_report),
            "technical_report": _as_json_data(technical_report),
            "news_report": _as_json_data(news_report),
            "portfolio_state": _as_json_data(portfolio_state),
            "risk_result": _as_json_data(risk_result),
            "risk_retry_count": risk_retry_count,
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._user_prompt(context)},
        ]
        last_error: DecisionLLMServiceError | None = None

        for attempt in range(self._max_retries + 1):
            try:
                completion = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=self._temperature,
                    response_format={"type": "json_object"},
                    timeout=self._timeout,
                )
                content = completion.choices[0].message.content
                if not isinstance(content, str) or not content.strip():
                    raise DecisionLLMResponseValidationError(
                        "DeepSeek returned empty content."
                    )
                proposal = TradeProposal.model_validate(json.loads(content))
                if contains_chinese(proposal.reason):
                    raise DecisionLLMResponseValidationError(
                        "DeepSeek decision reason must be in English only."
                    )
                return proposal
            except json.JSONDecodeError as error:
                last_error = DecisionLLMResponseValidationError(
                    "DeepSeek returned invalid JSON."
                )
                last_error.__cause__ = error
            except ValidationError as error:
                last_error = DecisionLLMResponseValidationError(
                    "DeepSeek JSON does not satisfy TradeProposal."
                )
                last_error.__cause__ = error
            except DecisionLLMResponseValidationError as error:
                last_error = error
            except Exception as error:
                last_error = DecisionLLMServiceError("DeepSeek request failed.")
                last_error.__cause__ = error

            if attempt < self._max_retries:
                self._sleeper(2**attempt)

        if isinstance(last_error, DecisionLLMResponseValidationError):
            raise last_error
        raise DecisionLLMServiceError("DeepSeek request failed after retries.") from last_error

    @staticmethod
    def _user_prompt(context: dict[str, Any]) -> str:
        """Constrain the model to the decision state supplied by the node."""
        return (
            "Return JSON only. Do not use outside knowledge. "
            "Write all natural-language fields in English only. "
            "Write reason entirely in English even when the input contains another "
            "language. Do not quote non-English text. "
            "Required JSON format: "
            '{"ticker":"AAPL","action":"BUY|SELL|HOLD","position_size":0.0,'
            '"entry_price":null,"stop_loss":null,"take_profit":null,'
            '"confidence":0.0,"reason":"..."}.\n'
            "Use the risk_result violations and risk_retry_count as feedback from the "
            "previous Python risk check. When violations are present, revise the proposal "
            "to address them numerically; an explanation alone is not a revision. "
            "For HOLD, position_size must be 0.0 because no trade is proposed. "
            "When MAX_POSITION_EXCEEDED is present, position_size must be no greater "
            "than 0.10. Do not claim that risk has approved it.\n"
            "Decision context:\n"
            f"{json.dumps(context, ensure_ascii=False, default=str)}"
        )


def _as_json_data(value: Any) -> Any:
    """Serialize Pydantic state values without exposing unrelated state fields."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


_shared_service: DecisionLLMService | None = None


def get_decision_llm_service() -> DecisionLLMService:
    """Return one shared DeepSeek decision service instance."""
    global _shared_service
    if _shared_service is None:
        _shared_service = DecisionLLMService()
    return _shared_service
