"""Routing decisions for the future FinGraph workflow."""

from typing import Any

from config.settings import MAX_RISK_RETRY
from graph.state import TradingState


def route_after_risk(state: TradingState) -> str:
    """Route risk outcomes to retry, HOLD completion, or human approval."""
    risk_result = state["risk_result"]
    approved = _value(risk_result, "approved")

    if approved:
        action = _value(state["trade_proposal"], "action")
        if action == "HOLD":
            return "hold"
        return "human_approval"
    if state["risk_retry_count"] < MAX_RISK_RETRY:
        return "retry"
    return "abort"


def route_after_human_approval(state: TradingState) -> str:
    """Execute only an explicitly approved proposal; reject ends the run."""
    return "execute" if state.get("human_approval") is True else "end"


def _value(item: Any, field: str) -> Any:
    """Read a field from either a Pydantic model or a dictionary."""
    if isinstance(item, dict):
        return item[field]
    return getattr(item, field)
