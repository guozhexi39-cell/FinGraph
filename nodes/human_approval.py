"""LangGraph interrupt/resume nodes for trade approval."""

from typing import Any

from langgraph.types import interrupt

from graph.state import TradingState


def human_approval_request_node(state: TradingState) -> dict[str, object]:
    """Record that a BUY or SELL proposal is waiting for a human decision."""
    return {
        "human_approval": None,
        "event_log": [*state.get("event_log", []), "Human approval requested"],
    }


def human_approval_node(state: TradingState) -> dict[str, object]:
    """Pause the graph and resume only after a human responds to the proposal."""
    response = interrupt(_approval_payload(state))
    approved = _approved_value(response)
    event = "Human approved trade" if approved else "Human rejected trade"

    return {
        "human_approval": approved,
        "event_log": [*state.get("event_log", []), event],
    }


def hold_completion_node(state: TradingState) -> dict[str, object]:
    """Finish a HOLD decision without asking for approval of a non-trade."""
    return {
        "human_approval": None,
        "event_log": [*state.get("event_log", []), "No human approval required for HOLD"],
    }


def _approval_payload(state: TradingState) -> dict[str, object]:
    """Return only the approved trade details, never prompts or credentials."""
    proposal = state["trade_proposal"]
    return {
        "ticker": _value(proposal, "ticker"),
        "action": _value(proposal, "action"),
        "position_size": _value(proposal, "position_size"),
        "entry_price": _value(proposal, "entry_price"),
        "stop_loss": _value(proposal, "stop_loss"),
        "take_profit": _value(proposal, "take_profit"),
        "confidence": _value(proposal, "confidence"),
        "reason": _value(proposal, "reason"),
        "risk_approved": True,
    }


def _approved_value(response: Any) -> bool:
    """Validate the explicit boolean decision supplied through Command(resume=...)."""
    value = response.get("approved") if isinstance(response, dict) else response
    if not isinstance(value, bool):
        raise ValueError("Human approval resume value must contain a boolean 'approved'.")
    return value


def _value(item: Any, field: str) -> Any:
    """Read fields from either Pydantic schemas or dictionary-shaped state."""
    if isinstance(item, dict):
        return item[field]
    return getattr(item, field)
