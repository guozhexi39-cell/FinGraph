"""News-analysis node with optional DeepSeek structured output."""

from config import settings
from graph.state import TradingState
from services import MockAnalystModel
from services.analyst_llm_service import get_analyst_llm_service

NEWS_SYSTEM_PROMPT = """You are an analyst responsible for company-related news.

Base your assessment only on the supplied news content and sentiment data.
Do not use company financial statements or stock price data.
Do not make the final trading decision.
Consider news titles, summaries, ticker relevance, ticker sentiment, consistency
across multiple articles, and any potentially significant risks.
Write all natural-language fields in English only, including summary, evidence,
and risks, even when the input contains another language. Do not quote non-English text.
Return JSON only."""


def news_agent_node(state: TradingState) -> dict[str, object]:
    """Analyze only ticker and news data with the model abstraction."""
    ticker = state["ticker"]
    news_data = state["news_data"]
    if settings.USE_REAL_ANALYST_LLM:
        report = get_analyst_llm_service().analyze(
            system_prompt=NEWS_SYSTEM_PROMPT,
            ticker=ticker,
            data=news_data,
        )
        event = "News agent completed with real LLM"
    else:
        model = MockAnalystModel()
        report = model.analyze_news(ticker, news_data)
        event = "News agent completed"

    return {
        "news_report": report,
        "event_log": [*state.get("event_log", []), event],
    }
