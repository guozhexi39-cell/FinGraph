"""Schema for the outcome of a future risk review."""

from pydantic import BaseModel


class RiskResult(BaseModel):
    """Risk-check decision and its evaluated rules."""

    approved: bool
    violations: list[str]
    checked_rules: list[str]
