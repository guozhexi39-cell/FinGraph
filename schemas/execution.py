"""Schema for a paper-broker execution outcome."""

from typing import Literal

from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """A normalized, validated result from an Alpaca paper order."""

    order_id: str
    ticker: str
    action: Literal["BUY", "SELL"]
    quantity: float = Field(gt=0)
    status: str
    submitted_at: str | None = None
    filled_at: str | None = None
    filled_price: float | None = Field(default=None, gt=0)
    paper_trade: Literal[True] = True
