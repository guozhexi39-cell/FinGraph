"""Decision node that combines the three independent analyst reports."""

from config import settings
from graph.state import TradingState
from services.decision_llm_service import get_decision_llm_service
from services.mock_decision_model import MockDecisionModel


DECISION_SYSTEM_PROMPT = """You are a portfolio decision-making agent.

Do not repeat the fundamental, technical, or news analysis. Combine the structured
reports of the three independent analyst agents with the current portfolio state
to generate a final trade proposal.
The only allowed actions are BUY, SELL, and HOLD. Consider each agent's signal and
confidence, significant disagreements, current cash and positions, the existing
position in this stock, and any risk feedback. When agents disagree significantly,
reduce confidence or choose a conservative proposal.
Do not assume data absent from the input or declare that risk checks have passed.
If the previous risk check rejected a proposal, revise it to address the violations.
position_size describes this proposed trade, not the account's existing position.
For HOLD, position_size must be 0.0. If violations include MAX_POSITION_EXCEEDED,
the revised position_size itself must be no greater than 0.10.
Write all natural-language fields in English only, including reason, even when
the input contains another language. Do not quote non-English text.
Return JSON only."""


def decision_agent_node(state: TradingState) -> dict[str, object]:
    """Create a trade proposal through the replaceable decision-model boundary."""
    if settings.USE_REAL_DECISION_LLM:
        proposal = get_decision_llm_service().propose_trade(
            system_prompt=DECISION_SYSTEM_PROMPT,
            ticker=state["ticker"],
            fundamental_report=state["fundamental_report"],
            technical_report=state["technical_report"],
            news_report=state["news_report"],
            portfolio_state=state["portfolio_state"],
            risk_result=state.get("risk_result"),
            risk_retry_count=state["risk_retry_count"],
        )
        event = (
            "Decision generated with real LLM "
            f"with position size {proposal.position_size:.2f}"
        )
    else:
        model = MockDecisionModel()
        proposal = model.propose_trade(
            ticker=state["ticker"],
            fundamental_report=state["fundamental_report"],
            technical_report=state["technical_report"],
            news_report=state["news_report"],
            portfolio_state=state["portfolio_state"],
            risk_result=state.get("risk_result"),
            risk_retry_count=state["risk_retry_count"],
        )
        event = f"Decision generated with position size {proposal.position_size:.2f}"

    return {
        "trade_proposal": proposal,
        "event_log": [*state.get("event_log", []), event],
    }
