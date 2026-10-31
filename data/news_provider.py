"""Alpha Vantage adapter for normalized ticker-specific market news."""

import os
from typing import Any
from urllib.parse import urlencode

from config import settings
from data.cache import DEFAULT_MARKET_DATA_CACHE, MarketDataCache
from data.exceptions import NewsDataProviderError, NewsDataValidationError
from data.market_provider import ALPHA_VANTAGE_URL, MarketDataProvider, Transport


class NewsDataProvider:
    """Fetch up to a configured number of ticker-filtered news articles."""

    source = "alpha_vantage"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        cache: MarketDataCache | None = None,
        cache_ttl: int | None = None,
        limit: int | None = None,
        transport: Transport | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("MARKET_DATA_API_KEY")
        self._cache = cache if cache is not None else DEFAULT_MARKET_DATA_CACHE
        self._cache_ttl = cache_ttl if cache_ttl is not None else settings.NEWS_DATA_CACHE_TTL
        self._limit = limit if limit is not None else settings.NEWS_DATA_LIMIT
        if self._limit < 1 or self._limit > 20:
            raise ValueError("limit must be between 1 and 20.")
        self._transport = transport if transport is not None else MarketDataProvider._fetch_json

    def get_news_data(self, ticker: str) -> list[dict[str, object]]:
        """Fetch, normalize, and cache ticker-specific recent news."""
        symbol = ticker.strip().upper()
        if not symbol:
            raise NewsDataValidationError("Ticker must not be empty.")

        cache_key = f"news:{symbol}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached["articles"]  # type: ignore[return-value]
        if not self._api_key:
            raise NewsDataProviderError(
                "MARKET_DATA_API_KEY must be configured for real news data."
            )

        payload = self._transport(self._build_url(symbol))
        self._raise_for_api_error(payload)
        articles = self._normalize(symbol, payload)
        self._cache.set(cache_key, {"articles": articles}, self._cache_ttl)
        return articles

    def _build_url(self, ticker: str) -> str:
        query = urlencode(
            {
                "function": "NEWS_SENTIMENT",
                "tickers": ticker,
                "sort": "LATEST",
                "limit": self._limit,
                "apikey": self._api_key,
            }
        )
        return f"{ALPHA_VANTAGE_URL}?{query}"

    @staticmethod
    def _raise_for_api_error(payload: dict[str, Any]) -> None:
        """Translate Alpha Vantage response errors into a domain exception."""
        if "Note" in payload:
            raise NewsDataProviderError("Alpha Vantage reported a rate limit.")
        if "Error Message" in payload or "Information" in payload:
            message = payload.get("Error Message") or payload.get("Information")
            raise NewsDataProviderError(f"Alpha Vantage news request failed: {message}")

    def _normalize(self, ticker: str, payload: dict[str, Any]) -> list[dict[str, object]]:
        """Map Alpha Vantage's feed into FinGraph's stable news contract."""
        feed = payload.get("feed")
        if not isinstance(feed, list) or not feed:
            raise NewsDataValidationError("News feed is empty.")

        articles: list[dict[str, object]] = []
        for raw_article in feed[: self._limit]:
            if not isinstance(raw_article, dict):
                raise NewsDataValidationError("News feed entry is invalid.")
            title = raw_article.get("title")
            if not isinstance(title, str) or not title.strip():
                raise NewsDataValidationError("News title is missing.")
            ticker_sentiment = _ticker_sentiment(raw_article, ticker)
            articles.append(
                {
                    "title": title.strip(),
                    "summary": _optional_text(raw_article.get("summary")),
                    "source": _optional_text(raw_article.get("source")),
                    "url": _optional_text(raw_article.get("url")),
                    "published_at": _optional_text(raw_article.get("time_published")),
                    "overall_sentiment_score": _optional_float(
                        raw_article.get("overall_sentiment_score")
                    ),
                    "overall_sentiment_label": _optional_text(
                        raw_article.get("overall_sentiment_label")
                    ),
                    "ticker_relevance_score": _optional_float(
                        ticker_sentiment.get("relevance_score")
                    ),
                    "ticker_sentiment_score": _optional_float(
                        ticker_sentiment.get("ticker_sentiment_score")
                    ),
                    "ticker_sentiment_label": _optional_text(
                        ticker_sentiment.get("ticker_sentiment_label")
                    ),
                }
            )
        return articles


def _ticker_sentiment(article: dict[str, Any], ticker: str) -> dict[str, Any]:
    """Return only the sentiment record matching the requested ticker."""
    sentiment = article.get("ticker_sentiment")
    if not isinstance(sentiment, list):
        return {}
    for entry in sentiment:
        if isinstance(entry, dict) and str(entry.get("ticker", "")).upper() == ticker:
            return entry
    return {}


def _optional_float(value: Any) -> float | None:
    """Parse a sentiment score without treating malformed optional data as a value."""
    if value is None or str(value).strip().lower() in {"", "none", "null", "-"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_text(value: Any) -> str | None:
    """Return a cleaned optional text field."""
    if value is None or str(value).strip().lower() in {"", "none", "null", "-"}:
        return None
    return str(value).strip()
