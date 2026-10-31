"""Schema for simulated portfolio holdings."""

from typing import Any

from pydantic import BaseModel


class PortfolioState(BaseModel):
    """Current cash, total value, and positions in a simulated portfolio."""

    cash: float
    total_value: float
    positions: dict[str, Any]
