"""Alpha Vantage adapter that returns FinGraph's normalized market-data shape."""

import json
import os
import ssl
from datetime import datetime, timezone
from time import sleep
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import certifi

from config import settings
from data.cache import DEFAULT_MARKET_DATA_CACHE, MarketDataCache
from data.exceptions import (
    MarketDataConfigurationError,
    MarketDataProviderError,
    MarketDataRateLimitError,
    MarketDataValidationError,
)

ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
Transport = Callable[[str], dict[str, Any]]
Sleeper = Callable[[float], None]


class MarketDataProvider:
    """Retrieve compact daily OHLCV data through the Alpha Vantage API."""

    source = "alpha_vantage"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        cache: MarketDataCache | None = None,
        cache_ttl: int | None = None,
        max_retries: int | None = None,
        history_days: int = 100,
        transport: Transport | None = None,
        sleeper: Sleeper = sleep,
    ) -> None:
        if history_days < 1 or history_days > 100:
            raise ValueError("history_days must be between 1 and 100.")
        self._api_key = api_key if api_key is not None else os.getenv("MARKET_DATA_API_KEY")
        self._cache = cache if cache is not None else DEFAULT_MARKET_DATA_CACHE
        self._cache_ttl = cache_ttl if cache_ttl is not None else settings.MARKET_DATA_CACHE_TTL
        self._max_retries = (
            max_retries if max_retries is not None else settings.MARKET_DATA_MAX_RETRIES
        )
        self._history_days = history_days
        self._transport = transport if transport is not None else self._fetch_json
        self._sleeper = sleeper

    def get_market_data(self, ticker: str) -> dict[str, object]:
        """Fetch, validate, normalize, and cache one ticker's daily market data."""
        symbol = ticker.strip().upper()
        if not symbol:
            raise MarketDataValidationError("Ticker must not be empty.")

        cached = self._cache.get(symbol)
        if cached is not None:
            return cached
        if not self._api_key:
            raise MarketDataConfigurationError(
                "MARKET_DATA_API_KEY must be configured for real market data."
            )

        last_error: MarketDataRateLimitError | None = None
        for attempt in range(self._max_retries):
            try:
                payload = self._transport(self._build_url(symbol))
                normalized = self._normalize(symbol, payload)
                self._cache.set(symbol, normalized, self._cache_ttl)
                return normalized
            except MarketDataRateLimitError as error:
                last_error = error
                if attempt < self._max_retries - 1:
                    self._sleeper(2**attempt)

        raise MarketDataRateLimitError(
            f"Alpha Vantage rate limit persisted after {self._max_retries} attempts."
        ) from last_error

    def _build_url(self, ticker: str) -> str:
        query = urlencode(
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "outputsize": "compact",
                "apikey": self._api_key,
            }
        )
        return f"{ALPHA_VANTAGE_URL}?{query}"

    @staticmethod
    def _fetch_json(url: str) -> dict[str, Any]:
        """Perform one API request and translate transport failures to domain errors."""
        try:
            with urlopen(  # noqa: S310 - fixed HTTPS endpoint
                url, timeout=10, context=SSL_CONTEXT
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429:
                raise MarketDataRateLimitError("Alpha Vantage returned HTTP 429.") from error
            raise MarketDataProviderError(
                f"Alpha Vantage returned HTTP {error.code}."
            ) from error
        except URLError as error:
            raise MarketDataProviderError("Unable to reach Alpha Vantage.") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise MarketDataProviderError("Alpha Vantage returned invalid JSON.") from error

    def _normalize(self, ticker: str, payload: dict[str, Any]) -> dict[str, object]:
        """Convert Alpha Vantage daily response JSON into the FinGraph contract."""
        if "Note" in payload:
            raise MarketDataRateLimitError("Alpha Vantage reported a rate limit.")
        if "Error Message" in payload or "Information" in payload:
            message = payload.get("Error Message") or payload.get("Information")
            raise MarketDataProviderError(f"Alpha Vantage request failed: {message}")

        raw_history = payload.get("Time Series (Daily)")
        if not isinstance(raw_history, dict) or not raw_history:
            raise MarketDataValidationError("Market-data history is empty.")

        history: list[dict[str, object]] = []
        for date, record in sorted(raw_history.items(), reverse=True)[: self._history_days]:
            if not isinstance(record, dict) or "4. close" not in record:
                raise MarketDataValidationError(
                    f"Market-data history entry {date} is missing close."
                )
            try:
                history.append(
                    {
                        "date": date,
                        "open": float(record["1. open"]),
                        "high": float(record["2. high"]),
                        "low": float(record["3. low"]),
                        "close": float(record["4. close"]),
                        "volume": int(float(record["5. volume"])),
                    }
                )
            except (KeyError, TypeError, ValueError) as error:
                raise MarketDataValidationError(
                    f"Market-data history entry {date} has invalid OHLCV values."
                ) from error

        current_price = history[0]["close"]
        if not isinstance(current_price, float) or current_price <= 0:
            raise MarketDataValidationError("Current price must be greater than zero.")

        return {
            "ticker": ticker,
            "current_price": current_price,
            "history": history,
            "source": self.source,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
