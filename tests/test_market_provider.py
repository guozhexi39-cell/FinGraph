"""Tests for the isolated, network-free Alpha Vantage market-data adapter."""

import pytest

from data.cache import MarketDataCache
from data.exceptions import MarketDataRateLimitError, MarketDataValidationError
from data.market_provider import MarketDataProvider


@pytest.fixture
def alpha_vantage_payload() -> dict[str, object]:
    return {
        "Meta Data": {"2. Symbol": "AAPL"},
        "Time Series (Daily)": {
            "2026-08-07": {
                "1. open": "205.00",
                "2. high": "212.00",
                "3. low": "204.00",
                "4. close": "210.00",
                "5. volume": "50000000",
            },
            "2026-08-06": {
                "1. open": "203.00",
                "2. high": "207.00",
                "3. low": "202.00",
                "4. close": "205.00",
                "5. volume": "45000000",
            },
        },
    }


def test_provider_normalizes_alpha_vantage_response(
    alpha_vantage_payload: dict[str, object],
) -> None:
    provider = MarketDataProvider(
        api_key="test-key",
        cache=MarketDataCache(),
        transport=lambda _url: alpha_vantage_payload,
    )

    data = provider.get_market_data("aapl")

    assert data["ticker"] == "AAPL"
    assert data["current_price"] == 210.0
    assert data["source"] == "alpha_vantage"
    assert data["history"] == [
        {
            "date": "2026-08-07",
            "open": 205.0,
            "high": 212.0,
            "low": 204.0,
            "close": 210.0,
            "volume": 50_000_000,
        },
        {
            "date": "2026-08-06",
            "open": 203.0,
            "high": 207.0,
            "low": 202.0,
            "close": 205.0,
            "volume": 45_000_000,
        },
    ]
    assert isinstance(data["fetched_at"], str)


def test_empty_history_raises_clear_validation_error() -> None:
    provider = MarketDataProvider(
        api_key="test-key",
        cache=MarketDataCache(),
        transport=lambda _url: {"Time Series (Daily)": {}},
    )

    with pytest.raises(MarketDataValidationError, match="history is empty"):
        provider.get_market_data("AAPL")


def test_non_positive_current_price_raises_clear_validation_error(
    alpha_vantage_payload: dict[str, object],
) -> None:
    alpha_vantage_payload["Time Series (Daily)"]["2026-08-07"]["4. close"] = "0"
    provider = MarketDataProvider(
        api_key="test-key",
        cache=MarketDataCache(),
        transport=lambda _url: alpha_vantage_payload,
    )

    with pytest.raises(MarketDataValidationError, match="greater than zero"):
        provider.get_market_data("AAPL")


def test_cache_hit_avoids_repeating_provider_request(
    alpha_vantage_payload: dict[str, object],
) -> None:
    calls = 0

    def transport(_url: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return alpha_vantage_payload

    provider = MarketDataProvider(
        api_key="test-key",
        cache=MarketDataCache(),
        transport=transport,
    )

    assert provider.get_market_data("AAPL")["current_price"] == 210.0
    assert provider.get_market_data("AAPL")["current_price"] == 210.0
    assert calls == 1


def test_rate_limit_retries_with_exponential_backoff_then_succeeds(
    alpha_vantage_payload: dict[str, object],
) -> None:
    calls = 0
    pauses: list[float] = []

    def transport(_url: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise MarketDataRateLimitError("HTTP 429")
        return alpha_vantage_payload

    provider = MarketDataProvider(
        api_key="test-key",
        cache=MarketDataCache(),
        max_retries=3,
        transport=transport,
        sleeper=pauses.append,
    )

    assert provider.get_market_data("AAPL")["current_price"] == 210.0
    assert calls == 3
    assert pauses == [1, 2]


def test_rate_limit_raises_after_the_configured_maximum_attempts() -> None:
    calls = 0

    def transport(_url: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        raise MarketDataRateLimitError("HTTP 429")

    provider = MarketDataProvider(
        api_key="test-key",
        cache=MarketDataCache(),
        max_retries=3,
        transport=transport,
        sleeper=lambda _seconds: None,
    )

    with pytest.raises(MarketDataRateLimitError, match="persisted after 3 attempts"):
        provider.get_market_data("AAPL")
    assert calls == 3
