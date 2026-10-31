"""Pure TradingState-to-dashboard view transformations."""

from typing import Any


def build_portfolio_view(portfolio: Any | None) -> dict[str, Any]:
    """Format normalized PortfolioState data without accessing any backend service."""
    if portfolio is None:
        return {"cash": None, "total_value": None, "position_count": 0, "positions": []}
    cash = _value(portfolio, "cash")
    total_value = _value(portfolio, "total_value")
    positions = _value(portfolio, "positions") or {}
    rows = [
        {
            "Ticker": ticker,
            "Quantity": _value(position, "quantity", default=0.0),
            "Market Value": _value(position, "market_value", default=0.0),
            "Position Size": format_percentage(
                _value(position, "position_size", default=0.0)
            ),
        }
        for ticker, position in positions.items()
    ]
    return {
        "cash": float(cash),
        "total_value": float(total_value),
        "position_count": len(rows),
        "positions": rows,
    }


def build_agent_view(report: Any | None) -> dict[str, Any] | None:
    """Convert an AnalystReport to concise signal, confidence, and detail fields."""
    if report is None:
        return None
    confidence = float(_value(report, "confidence"))
    return {
        "signal": str(_value(report, "signal")).upper(),
        "confidence": confidence,
        "confidence_display": format_percentage(confidence),
        "summary": str(_value(report, "summary")),
        "evidence": list(_value(report, "evidence")),
        "risks": list(_value(report, "risks")),
    }


def detect_agent_disagreement(state: dict[str, Any]) -> dict[str, Any]:
    """Report whether the available analyst signals are not all the same."""
    signals = {
        label: str(_value(report, "signal"))
        for label, report in (
            ("Fundamental", state.get("fundamental_report")),
            ("Technical", state.get("technical_report")),
            ("News", state.get("news_report")),
        )
        if report is not None
    }
    return {"detected": len(set(signals.values())) > 1, "signals": signals}


def build_decision_view(proposal: Any | None) -> dict[str, Any] | None:
    """Convert a TradeProposal to dashboard fields."""
    if proposal is None:
        return None
    position_size = float(_value(proposal, "position_size"))
    return {
        "ticker": str(_value(proposal, "ticker")),
        "action": str(_value(proposal, "action")),
        "position_size": position_size,
        "position_size_display": format_percentage(position_size),
        "entry_price": _value(proposal, "entry_price"),
        "stop_loss": _value(proposal, "stop_loss"),
        "take_profit": _value(proposal, "take_profit"),
        "confidence": float(_value(proposal, "confidence")),
        "confidence_display": format_percentage(_value(proposal, "confidence")),
        "reason": str(_value(proposal, "reason")),
    }


def build_risk_view(result: Any | None, retry_count: int | None) -> dict[str, Any] | None:
    """Convert a RiskResult and retry count to a small read-only view model."""
    if result is None:
        return None
    return {
        "approved": bool(_value(result, "approved")),
        "violations": list(_value(result, "violations")),
        "checked_rules": list(_value(result, "checked_rules")),
        "retry_count": retry_count or 0,
    }


def build_execution_view(result: Any | None) -> dict[str, Any] | None:
    """Convert an ExecutionResult to a display-only summary."""
    if result is None:
        return None
    return {
        "ticker": str(_value(result, "ticker")),
        "action": str(_value(result, "action")),
        "quantity": float(_value(result, "quantity")),
        "order_id": str(_value(result, "order_id")),
        "status": str(_value(result, "status")),
        "submitted_at": _value(result, "submitted_at"),
        "filled_at": _value(result, "filled_at"),
        "filled_price": _value(result, "filled_price"),
        "paper_trade": bool(_value(result, "paper_trade")),
    }


def serializable_state(state: dict[str, Any] | None) -> dict[str, Any]:
    """Return a safe, JSON-friendly state view without secrets or prompts."""
    if not state:
        return {}
    return {
        key: _serialize(value)
        for key, value in state.items()
        if not _sensitive_key(key)
    }


def format_percentage(value: float | int) -> str:
    """Render a fractional position or confidence as a compact percentage."""
    return f"{float(value):.0%}"


def _value(item: Any, field: str, *, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(field, default)
    return getattr(item, field, default)


def _serialize(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _serialize(value.model_dump())
    if isinstance(value, dict):
        return {
            key: _serialize(item)
            for key, item in value.items()
            if not _sensitive_key(str(key))
        }
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    return value


def _sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in ("api_key", "secret", "authorization", "prompt"))
