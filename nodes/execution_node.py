"""Paper-only execution node following explicit human approval."""

from typing import Any

from config import settings
from execution import AlpacaPaperBroker
from graph.state import TradingState


def execution_node(state: TradingState) -> dict[str, object]:
    """Submit an approved BUY or SELL to Alpaca's paper environment only."""
    proposal = state["trade_proposal"]
    action = _value(proposal, "action")
    event_log = [*state.get("event_log", [])]

    if action == "HOLD":
        return {"event_log": [*event_log, "Execution skipped for HOLD"]}
    if state.get("human_approval") is not True:
        return {"event_log": [*event_log, "Execution skipped without human approval"]}
    if not settings.USE_PAPER_TRADING:
        return {"event_log": [*event_log, "Paper trading disabled; no order submitted"]}

    quantity = calculate_order_quantity(state)
    result = get_paper_broker().submit_market_order(
        ticker=_value(proposal, "ticker"),
        action=action,
        quantity=quantity,
    )
    return {
        "execution_result": result,
        "event_log": [
            *event_log,
            f"Paper order submitted: {action} {_value(proposal, 'ticker')} {quantity}",
        ],
    }


def calculate_order_quantity(state: TradingState) -> float:
    """Calculate fractional market-order quantity in Python, not via an LLM."""
    proposal = state["trade_proposal"]
    portfolio = state["portfolio_state"]
    market_data = state["market_data"]
    position_size = float(_value(proposal, "position_size"))
    total_value = float(_value(portfolio, "total_value"))
    current_price = float(_value(market_data, "current_price"))
    if position_size <= 0:
        raise ValueError("Trade proposal position_size must be greater than zero.")
    if total_value <= 0:
        raise ValueError("Portfolio total_value must be greater than zero.")
    if current_price <= 0:
        raise ValueError("Current market price must be greater than zero.")
    return round((total_value * position_size) / current_price, 6)


def get_paper_broker() -> AlpacaPaperBroker:
    """Construct the paper-only broker only when execution has been authorized."""
    return AlpacaPaperBroker()


def _value(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item[field]
    return getattr(item, field)
