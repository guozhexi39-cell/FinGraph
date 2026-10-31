"""Network-isolated tests for the Alpha Vantage news-data adapter."""

from urllib.parse import parse_qs, urlparse

import pytest

from data.cache import MarketDataCache
from data.exceptions import NewsDataValidationError
from data.news_provider import NewsDataProvider


@pytest.fixture
def news_payload() -> dict[str, object]:
    return {
        "feed": [
            {
                "title": "Apple demand remains resilient",
                "summary": "A summary.",
                "source": "Example Wire",
                "url": "https://example.com/aapl",
                "time_published": "20260807T120000",
                "overall_sentiment_score": "0.25",
                "overall_sentiment_label": "Somewhat-Bullish",
                "ticker_sentiment": [
                    {
                        "ticker": "MSFT",
                        "relevance_score": "0.1",
                        "ticker_sentiment_score": "-0.2",
                        "ticker_sentiment_label": "Bearish",
                    },
                    {
                        "ticker": "AAPL",
                        "relevance_score": "0.9",
                        "ticker_sentiment_score": "0.35",
                        "ticker_sentiment_label": "Bullish",
                    },
                ],
            },
            {
                "title": "Apple launches product update",
                "summary": None,
                "source": "Another Wire",
                "url": "https://example.com/aapl-2",
                "time_published": "20260806T120000",
                "overall_sentiment_score": "not-a-number",
                "overall_sentiment_label": "Neutral",
                "ticker_sentiment": [],
            },
            {
                "title": "Third Apple article",
                "summary": "Third summary.",
                "source": "Third Wire",
                "url": "https://example.com/aapl-3",
                "time_published": "20260805T120000",
            },
        ]
    }


def _provider(
    payload: dict[str, object],
    *,
    cache: MarketDataCache | None = None,
    cache_ttl: int | None = None,
    limit: int = 20,
) -> NewsDataProvider:
    def transport(url: str) -> dict[str, object]:
        query = parse_qs(urlparse(url).query)
        assert query["function"] == ["NEWS_SENTIMENT"]
        assert query["tickers"] == ["AAPL"]
        assert query["sort"] == ["LATEST"]
        assert query["limit"] == [str(limit)]
        return payload

    return NewsDataProvider(
        api_key="test-key",
        cache=cache if cache is not None else MarketDataCache(),
        cache_ttl=cache_ttl,
        limit=limit,
        transport=transport,
    )


def test_provider_normalizes_news_and_extracts_target_ticker_sentiment(
    news_payload: dict[str, object],
) -> None:
    articles = _provider(news_payload).get_news_data("aapl")
    article = articles[0]

    assert article["title"] == "Apple demand remains resilient"
    assert article["source"] == "Example Wire"
    assert article["published_at"] == "20260807T120000"
    assert article["overall_sentiment_score"] == 0.25
    assert article["ticker_relevance_score"] == 0.9
    assert article["ticker_sentiment_score"] == 0.35
    assert article["ticker_sentiment_label"] == "Bullish"


def test_invalid_optional_sentiment_score_becomes_none(
    news_payload: dict[str, object],
) -> None:
    articles = _provider(news_payload).get_news_data("AAPL")

    assert articles[1]["overall_sentiment_score"] is None
    assert articles[1]["ticker_relevance_score"] is None


def test_empty_news_feed_raises_clear_error() -> None:
    with pytest.raises(NewsDataValidationError, match="feed is empty"):
        _provider({"feed": []}).get_news_data("AAPL")


def test_news_result_is_limited_to_configured_size(
    news_payload: dict[str, object],
) -> None:
    articles = _provider(news_payload, limit=2).get_news_data("AAPL")

    assert len(articles) == 2


def test_cache_hit_avoids_a_second_api_request(news_payload: dict[str, object]) -> None:
    calls = 0

    def transport(_url: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return news_payload

    provider = NewsDataProvider(
        api_key="test-key", cache=MarketDataCache(), transport=transport
    )

    provider.get_news_data("AAPL")
    provider.get_news_data("AAPL")

    assert calls == 1


def test_expired_cache_repeats_the_api_request(news_payload: dict[str, object]) -> None:
    now = 0.0

    def clock() -> float:
        return now

    calls = 0

    def transport(_url: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return news_payload

    provider = NewsDataProvider(
        api_key="test-key",
        cache=MarketDataCache(clock=clock),
        cache_ttl=10,
        transport=transport,
    )

    provider.get_news_data("AAPL")
    now = 11.0
    provider.get_news_data("AAPL")

    assert calls == 2
