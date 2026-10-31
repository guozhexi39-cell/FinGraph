"""Technical-analysis node with optional DeepSeek structured output."""

from config import settings
from graph.state import TradingState
from services import MockAnalystModel
from services.analyst_llm_service import get_analyst_llm_service

TECHNICAL_SYSTEM_PROMPT = """You are a technical-analysis agent responsible for stock price trends.

Analyze only the supplied historical price and volume data.
Do not use company news or fundamental information.
Do not make the final trading decision.
Do not claim to use MA, RSI, MACD, or other indicators unless they are supplied.
Analyze only recent price movements, direction, volatility, volume changes, and
trends actually present in the input.
Write all natural-language fields in English only, including summary, evidence,
and risks, even when the input contains another language. Do not quote non-English text.
Return JSON only."""


def technical_agent_node(state: TradingState) -> dict[str, object]:
    """Analyze only ticker and market data with the model abstraction."""
    ticker = state["ticker"]
    market_data = state["market_data"]
    if settings.USE_REAL_ANALYST_LLM:
        report = get_analyst_llm_service().analyze(
            system_prompt=TECHNICAL_SYSTEM_PROMPT,
            ticker=ticker,
            data=market_data,
        )
        event = "Technical agent completed with real LLM"
    else:
        model = MockAnalystModel()
        report = model.analyze_technical(ticker, market_data)
        event = "Technical agent completed"

    return {
        "technical_report": report,
        "event_log": [*state.get("event_log", []), event],
    }
