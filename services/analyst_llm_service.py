"""Shared DeepSeek service for structured analyst reports."""

import json
import os
from time import sleep
from typing import Any, Callable

from openai import OpenAI
from pydantic import ValidationError

from config import settings
from schemas import AnalystReport
from services.response_language import contains_chinese

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
Sleeper = Callable[[float], None]


class AnalystLLMServiceError(Exception):
    """Raised when the DeepSeek analyst service cannot complete a request."""


class LLMConfigurationError(AnalystLLMServiceError):
    """Raised when DeepSeek credentials are not configured."""


class LLMResponseValidationError(AnalystLLMServiceError):
    """Raised when model output is empty, non-JSON, or schema-invalid."""


class AnalystLLMService:
    """Call DeepSeek once per analysis with retrying, validated JSON output."""

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
            temperature if temperature is not None else settings.ANALYST_LLM_TEMPERATURE
        )
        self._max_retries = (
            max_retries if max_retries is not None else settings.ANALYST_LLM_MAX_RETRIES
        )
        self._timeout = timeout if timeout is not None else settings.ANALYST_LLM_TIMEOUT
        if self._max_retries < 0:
            raise ValueError("max_retries must not be negative.")
        if client is None:
            if not self._api_key:
                raise LLMConfigurationError("DEEPSEEK_API_KEY must be configured.")
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=DEEPSEEK_BASE_URL,
                timeout=self._timeout,
            )
        else:
            self._client = client
        self._sleeper = sleeper

    def analyze(
        self, *, system_prompt: str, ticker: str, data: dict[str, Any] | list[dict[str, Any]]
    ) -> AnalystReport:
        """Analyze only the caller-supplied data and validate an AnalystReport."""
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": self._user_prompt(ticker, data),
            },
        ]
        last_error: AnalystLLMServiceError | None = None

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
                    raise LLMResponseValidationError("DeepSeek returned empty content.")
                report = AnalystReport.model_validate(json.loads(content))
                if any(contains_chinese(text) for text in (
                    report.summary, *report.evidence, *report.risks,
                )):
                    raise LLMResponseValidationError(
                        "DeepSeek analyst text must be in English only."
                    )
                return report
            except json.JSONDecodeError as error:
                last_error = LLMResponseValidationError(
                    "DeepSeek returned invalid JSON."
                )
                last_error.__cause__ = error
            except ValidationError as error:
                last_error = LLMResponseValidationError(
                    "DeepSeek JSON does not satisfy AnalystReport."
                )
                last_error.__cause__ = error
            except LLMResponseValidationError as error:
                last_error = error
            except Exception as error:
                last_error = AnalystLLMServiceError("DeepSeek request failed.")
                last_error.__cause__ = error

            if attempt < self._max_retries:
                self._sleeper(2**attempt)

        if isinstance(last_error, LLMResponseValidationError):
            raise last_error
        raise AnalystLLMServiceError("DeepSeek request failed after retries.") from last_error

    @staticmethod
    def _user_prompt(
        ticker: str, data: dict[str, Any] | list[dict[str, Any]],
    ) -> str:
        """Constrain the model to the selected agent's supplied data only."""
        return (
            "Return JSON only. Do not use outside knowledge. "
            "Write all natural-language fields in English only. "
            "This includes summary, every evidence item, and every risk item, even "
            "when the input contains another language. Do not quote non-English text. "
            "Required JSON format: "
            '{"signal":"bullish|bearish|neutral","confidence":0.0,'
            '"evidence":["..."],"risks":["..."],"summary":"..."}.\n'
            f"Ticker: {ticker}\n"
            "Input data:\n"
            f"{json.dumps(data, ensure_ascii=False, default=str)}"
        )


_shared_service: AnalystLLMService | None = None


def get_analyst_llm_service() -> AnalystLLMService:
    """Return one shared client service for every real analyst node."""
    global _shared_service
    if _shared_service is None:
        _shared_service = AnalystLLMService()
    return _shared_service
