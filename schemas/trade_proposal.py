"""Schema for a proposed simulated trade."""

from typing import Literal

from pydantic import BaseModel, Field


class TradeProposal(BaseModel):
    """A trade recommendation before risk review or approval."""

    ticker: str
    action: Literal["BUY", "SELL", "HOLD"]
    position_size: float = Field(ge=0, le=1)
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    confidence: float = Field(ge=0, le=1)
    reason: str
