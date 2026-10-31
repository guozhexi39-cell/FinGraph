"""Fundamental-analysis node with optional DeepSeek structured output."""

from config import settings
from graph.state import TradingState
from services import MockAnalystModel
from services.analyst_llm_service import get_analyst_llm_service

FUNDAMENTAL_SYSTEM_PROMPT = """You are a financial analyst responsible for company fundamentals.

Base your assessment only on the supplied company fundamental data.
Do not assume missing data or supplement the input with outside knowledge.
Do not make the final trading decision.
Your task is only to assess the company's fundamental condition.

Focus on revenue growth, profit growth, PE ratio, EPS, profit margin, market cap,
sector, industry, and other fundamental information explicitly present in the data.
Write all natural-language fields in English only, including summary, evidence,
and risks, even when the input contains another language. Do not quote non-English text.
Return JSON only."""


def fundamental_agent_node(state: TradingState) -> dict[str, object]:
    """Analyze only ticker and fundamental data with the model abstraction."""
    ticker = state["ticker"]
    fundamental_data = state["fundamental_data"]
    if settings.USE_REAL_ANALYST_LLM:
        report = get_analyst_llm_service().analyze(
            system_prompt=FUNDAMENTAL_SYSTEM_PROMPT,
            ticker=ticker,
            data=fundamental_data,
        )
        event = "Fundamental agent completed with real LLM"
    else:
        model = MockAnalystModel()
        report = model.analyze_fundamental(ticker, fundamental_data)
        event = "Fundamental agent completed"

    return {
        "fundamental_report": report,
        "event_log": [*state.get("event_log", []), event],
    }
