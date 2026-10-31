"""Alpha Vantage adapter for normalized company fundamental data."""

import os
from datetime import datetime, timezone
from time import sleep
from typing import Any
from urllib.parse import urlencode

from config import settings
from data.cache import DEFAULT_MARKET_DATA_CACHE, MarketDataCache
from data.exceptions import (
    FundamentalDataProviderError,
    FundamentalDataValidationError,
)
from data.market_provider import (
    ALPHA_VANTAGE_URL,
    MarketDataProvider,
    Sleeper,
    Transport,
)


class FundamentalDataProvider:
    """Fetch OVERVIEW and INCOME_STATEMENT data for one ticker."""

    source = "alpha_vantage"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        cache: MarketDataCache | None = None,
        cache_ttl: int | None = None,
        transport: Transport | None = None,
        request_interval_seconds: float = 1.1,
        sleeper: Sleeper = sleep,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("MARKET_DATA_API_KEY")
        self._cache = cache if cache is not None else DEFAULT_MARKET_DATA_CACHE
        self._cache_ttl = (
            cache_ttl
            if cache_ttl is not None
            else settings.FUNDAMENTAL_DATA_CACHE_TTL
        )
        self._transport = transport if transport is not None else MarketDataProvider._fetch_json
        self._request_interval_seconds = request_interval_seconds
        self._sleeper = sleeper

    def get_fundamental_data(self, ticker: str) -> dict[str, object]:
        """Fetch, validate, normalize, and cache one company's fundamentals."""
        symbol = ticker.strip().upper()
        if not symbol:
            raise FundamentalDataValidationError("Ticker must not be empty.")

        cache_key = f"fundamental:{symbol}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        if not self._api_key:
            raise FundamentalDataProviderError(
                "MARKET_DATA_API_KEY must be configured for real fundamental data."
            )

        overview = self._request("OVERVIEW", symbol)
        self._sleeper(self._request_interval_seconds)
        income_statement = self._request("INCOME_STATEMENT", symbol)
        normalized = self._normalize(symbol, overview, income_statement)
        self._cache.set(cache_key, normalized, self._cache_ttl)
        return normalized

    def _request(self, function: str, ticker: str) -> dict[str, Any]:
        """Request one Alpha Vantage fundamental endpoint without exposing the key."""
        query = urlencode(
            {"function": function, "symbol": ticker, "apikey": self._api_key}
        )
        payload = self._transport(f"{ALPHA_VANTAGE_URL}?{query}")
        if "Note" in payload:
            raise FundamentalDataProviderError("Alpha Vantage reported a rate limit.")
        if "Error Message" in payload or "Information" in payload:
            message = payload.get("Error Message") or payload.get("Information")
            raise FundamentalDataProviderError(
                f"Alpha Vantage {function} request failed: {message}"
            )
        return payload

    def _normalize(
        self,
        ticker: str,
        overview: dict[str, Any],
        income_statement: dict[str, Any],
    ) -> dict[str, object]:
        """Convert both endpoint responses into FinGraph's stable data shape."""
        if not overview:
            raise FundamentalDataValidationError("Alpha Vantage overview is empty.")
        company_name = overview.get("Name")
        if not isinstance(company_name, str) or not company_name.strip():
            raise FundamentalDataValidationError("Fundamental company_name is missing.")

        current_report, previous_report = self._latest_two_reports(income_statement)
        revenue = _required_number(current_report.get("totalRevenue"), "revenue")
        previous_revenue = _required_number(
            previous_report.get("totalRevenue"), "previous_revenue"
        )
        net_income = _required_number(current_report.get("netIncome"), "net_income")
        previous_net_income = _required_number(
            previous_report.get("netIncome"), "previous_net_income"
        )

        return {
            "ticker": ticker,
            "company_name": company_name.strip(),
            "sector": _optional_text(overview.get("Sector")),
            "industry": _optional_text(overview.get("Industry")),
            "market_cap": _optional_number(overview.get("MarketCapitalization")),
            "pe_ratio": _optional_number(overview.get("PERatio")),
            "eps": _optional_number(overview.get("EPS")),
            "profit_margin": _optional_number(overview.get("ProfitMargin")),
            "revenue": revenue,
            "previous_revenue": previous_revenue,
            "revenue_growth": calculate_growth(revenue, previous_revenue),
            "net_income": net_income,
            "previous_net_income": previous_net_income,
            "profit_growth": calculate_growth(net_income, previous_net_income),
            "source": self.source,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _latest_two_reports(
        income_statement: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Choose the two most recent annual reports, or quarterly reports as fallback."""
        reports = income_statement.get("annualReports")
        if not isinstance(reports, list) or len(reports) < 2:
            reports = income_statement.get("quarterlyReports")
        if not isinstance(reports, list) or len(reports) < 2:
            raise FundamentalDataValidationError(
                "Income statement requires at least two annual or quarterly reports."
            )
        try:
            ordered_reports = sorted(
                reports,
                key=lambda report: report["fiscalDateEnding"],
                reverse=True,
            )
            current_report, previous_report = ordered_reports[:2]
        except (KeyError, TypeError) as error:
            raise FundamentalDataValidationError(
                "Income statement reports require fiscalDateEnding."
            ) from error
        if not isinstance(current_report, dict) or not isinstance(previous_report, dict):
            raise FundamentalDataValidationError("Income statement reports are invalid.")
        return current_report, previous_report


def calculate_growth(current: float | None, previous: float | None) -> float | None:
    """Calculate growth safely, including negative profits and zero denominators."""
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / abs(previous)


def _required_number(value: Any, field_name: str) -> float:
    """Parse a required income-statement number or raise a clear error."""
    result = _optional_number(value)
    if result is None:
        raise FundamentalDataValidationError(
            f"Fundamental {field_name} must be a numeric value."
        )
    return result


def _optional_number(value: Any) -> float | None:
    """Convert an optional Alpha Vantage numeric field without inventing a value."""
    if value is None or str(value).strip().lower() in {"", "none", "null", "-"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise FundamentalDataValidationError(
            f"Fundamental numeric value is invalid: {value!r}."
        ) from error


def _optional_text(value: Any) -> str | None:
    """Return a cleaned optional string, treating provider placeholders as missing."""
    if value is None or str(value).strip().lower() in {"", "none", "null", "-"}:
        return None
    return str(value).strip()
