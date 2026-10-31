"""Schema for an analyst's stock assessment."""

from typing import Literal

from pydantic import BaseModel, Field


class AnalystReport(BaseModel):
    """A concise assessment returned by an analysis source."""

    signal: Literal["bullish", "bearish", "neutral"]
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]
    risks: list[str]
    summary: str
