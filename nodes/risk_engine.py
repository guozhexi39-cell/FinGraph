"""Pure-Python trade-proposal risk checks."""

from typing import Any

from config.settings import MAX_RISK_RETRY, MAX_POSITION_SIZE
from graph.state import TradingState
from schemas import RiskResult

CHECKED_RULES = [
    "MAX_POSITION_SIZE",
    "CASH_AVAILABLE",
    "STOP_LOSS_REQUIRED",
    "VALID_POSITION_SIZE",
]


def risk_engine_node(state: TradingState) -> dict[str, object]:
    """Validate a proposal and return the risk outcome plus retry state."""
    proposal = state["trade_proposal"]
    portfolio = state["portfolio_state"]
    position_size = _value(proposal, "position_size")
    action = _value(proposal, "action")
    stop_loss = _value(proposal, "stop_loss")
    violations: list[str] = []

    if position_size > MAX_POSITION_SIZE:
        violations.append("MAX_POSITION_EXCEEDED")

    if action == "BUY":
        required_cash = _value(portfolio, "total_value") * position_size
        if required_cash > _value(portfolio, "cash"):
            violations.append("INSUFFICIENT_CASH")
        if stop_loss is None:
            violations.append("STOP_LOSS_REQUIRED")

    if not 0 <= position_size <= 1:
        violations.append("INVALID_POSITION_SIZE")

    result = RiskResult(
        approved=not violations,
        violations=violations,
        checked_rules=CHECKED_RULES,
    )
    event_log = [*state.get("event_log", [])]

    if result.approved:
        event_log.append("Risk approved proposal")
        return {
            "risk_result": result,
            "risk_retry_count": state["risk_retry_count"],
            "event_log": event_log,
        }

    retry_count = state["risk_retry_count"] + 1
    event_log.append(f"Risk rejected proposal: {', '.join(violations)}")
    event_log.append(f"Retrying decision: {retry_count}/{MAX_RISK_RETRY}")
    return {
        "risk_result": result,
        "risk_retry_count": retry_count,
        "event_log": event_log,
    }


def _value(item: Any, field: str) -> Any:
    """Support schema objects and dictionary-shaped state values."""
    if isinstance(item, dict):
        return item[field]
    return getattr(item, field)
