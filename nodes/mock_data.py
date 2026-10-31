"""Mock data with an optional real market-data replacement."""

from config import settings
from data.fundamental_provider import FundamentalDataProvider
from data.market_provider import MarketDataProvider
from data.news_provider import NewsDataProvider
from graph.state import TradingState
from schemas import PortfolioState


def mock_data_node(state: TradingState) -> dict[str, object]:
    """Load real market data when enabled; retain mock data for all other fields."""
    ticker = state["ticker"]
    if settings.USE_REAL_MARKET_DATA:
        market_data = MarketDataProvider().get_market_data(ticker)
        data_event = "Real market data loaded"
    else:
        market_data = {
            "current_price": 210.0,
            "price_change_5d": 0.04,
            "volatility": 0.22,
        }
        data_event = "Mock data loaded"
    if settings.USE_REAL_FUNDAMENTAL_DATA:
        fundamental_data = FundamentalDataProvider().get_fundamental_data(ticker)
        fundamental_event = "Real fundamental data loaded"
    else:
        fundamental_data = {
            "revenue_growth": 0.08,
            "profit_growth": 0.06,
            "debt_level": "medium",
        }
        fundamental_event = None
    if settings.USE_REAL_NEWS_DATA:
        news_data = NewsDataProvider().get_news_data(ticker)
        news_event = "Real news data loaded"
    else:
        news_data = [
            {
                "headline": "Company reports stronger than expected demand",
                "sentiment_hint": "positive",
            }
        ]
        news_event = None
    event_log = [*state.get("event_log", []), data_event]
    if fundamental_event:
        event_log.append(fundamental_event)
    if news_event:
        event_log.append(news_event)
    portfolio = PortfolioState(
        cash=80_000,
        total_value=100_000,
        positions={
            "AAPL": {
                "quantity": 100,
                "market_value": 20_000,
                "position_size": 0.20,
            }
        },
    )

    return {
        "market_data": market_data,
        "fundamental_data": fundamental_data,
        "news_data": news_data,
        "portfolio_state": portfolio.model_dump(),
        "risk_retry_count": 0,
        "event_log": event_log,
    }
