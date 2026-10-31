"""Network-isolated tests for the Alpha Vantage fundamental-data adapter."""

from urllib.parse import parse_qs, urlparse

import pytest

from data.cache import MarketDataCache
from data.exceptions import FundamentalDataValidationError
from data.fundamental_provider import FundamentalDataProvider, calculate_growth


@pytest.fixture
def overview_payload() -> dict[str, str]:
    return {
        "Name": "Apple Inc",
        "Sector": "TECHNOLOGY",
        "Industry": "ELECTRONIC COMPUTERS",
        "MarketCapitalization": "3000000000000",
        "PERatio": "30.5",
        "EPS": "7.50",
        "ProfitMargin": "0.25",
    }


@pytest.fixture
def income_statement_payload() -> dict[str, object]:
    return {
        "annualReports": [
            {
                "fiscalDateEnding": "2025-09-30",
                "totalRevenue": "120",
                "netIncome": "24",
            },
            {
                "fiscalDateEnding": "2024-09-30",
                "totalRevenue": "100",
                "netIncome": "20",
            },
        ]
    }


def _provider(
    overview: dict[str, object],
    income_statement: dict[str, object],
    *,
    cache: MarketDataCache | None = None,
    cache_ttl: int | None = None,
) -> FundamentalDataProvider:
    def transport(url: str) -> dict[str, object]:
        function = parse_qs(urlparse(url).query)["function"][0]
        return overview if function == "OVERVIEW" else income_statement

    return FundamentalDataProvider(
        api_key="test-key",
        cache=cache if cache is not None else MarketDataCache(),
        cache_ttl=cache_ttl,
        transport=transport,
        request_interval_seconds=0,
    )


def test_provider_normalizes_overview_and_recent_income_reports(
    overview_payload: dict[str, object], income_statement_payload: dict[str, object]
) -> None:
    data = _provider(overview_payload, income_statement_payload).get_fundamental_data(
        "aapl"
    )

    assert data["ticker"] == "AAPL"
    assert data["company_name"] == "Apple Inc"
    assert data["sector"] == "TECHNOLOGY"
    assert data["market_cap"] == 3_000_000_000_000.0
    assert data["pe_ratio"] == 30.5
    assert data["eps"] == 7.5
    assert data["profit_margin"] == 0.25
    assert data["revenue"] == 120.0
    assert data["previous_revenue"] == 100.0
    assert data["net_income"] == 24.0
    assert data["previous_net_income"] == 20.0
    assert data["source"] == "alpha_vantage"


def test_revenue_and_profit_growth_are_calculated_from_two_reports(
    overview_payload: dict[str, object], income_statement_payload: dict[str, object]
) -> None:
    data = _provider(overview_payload, income_statement_payload).get_fundamental_data(
        "AAPL"
    )

    assert data["revenue_growth"] == 0.2
    assert data["profit_growth"] == 0.2


def test_zero_previous_value_returns_none_without_dividing_by_zero() -> None:
    assert calculate_growth(120.0, 0.0) is None
    assert calculate_growth(-20.0, -10.0) == -1.0


def test_empty_overview_raises_clear_error(
    income_statement_payload: dict[str, object],
) -> None:
    provider = _provider({}, income_statement_payload)

    with pytest.raises(FundamentalDataValidationError, match="overview is empty"):
        provider.get_fundamental_data("AAPL")


def test_insufficient_income_reports_raises_clear_error(
    overview_payload: dict[str, object],
) -> None:
    provider = _provider(
        overview_payload,
        {"annualReports": [{"fiscalDateEnding": "2025-09-30"}]},
    )

    with pytest.raises(FundamentalDataValidationError, match="at least two"):
        provider.get_fundamental_data("AAPL")


def test_cache_hit_does_not_repeat_either_api_request(
    overview_payload: dict[str, object], income_statement_payload: dict[str, object]
) -> None:
    calls = 0

    def transport(url: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        function = parse_qs(urlparse(url).query)["function"][0]
        return overview_payload if function == "OVERVIEW" else income_statement_payload

    provider = FundamentalDataProvider(
        api_key="test-key",
        cache=MarketDataCache(),
        transport=transport,
        request_interval_seconds=0,
    )

    provider.get_fundamental_data("AAPL")
    provider.get_fundamental_data("AAPL")

    assert calls == 2


def test_expired_cache_repeats_both_api_requests(
    overview_payload: dict[str, object], income_statement_payload: dict[str, object]
) -> None:
    now = 0.0

    def clock() -> float:
        return now

    calls = 0

    def transport(url: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        function = parse_qs(urlparse(url).query)["function"][0]
        return overview_payload if function == "OVERVIEW" else income_statement_payload

    cache = MarketDataCache(clock=clock)
    provider = FundamentalDataProvider(
        api_key="test-key",
        cache=cache,
        cache_ttl=10,
        transport=transport,
        request_interval_seconds=0,
    )

    provider.get_fundamental_data("AAPL")
    now = 11.0
    provider.get_fundamental_data("AAPL")

    assert calls == 4
