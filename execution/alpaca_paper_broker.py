"""Alpaca adapter that is permanently restricted to the paper environment."""

import os
from typing import Any, Callable

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from schemas import ExecutionResult, PortfolioState

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
PAPER_API_ENDPOINT = f"{PAPER_BASE_URL}/v2"
ClientFactory = Callable[..., Any]


class PaperBrokerError(RuntimeError):
    """Raised when an Alpaca paper API operation fails."""


class AlpacaPaperBroker:
    """Translate FinGraph execution requests to Alpaca paper-only operations."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        secret_key: str | None = None,
        client: Any | None = None,
        client_factory: ClientFactory = TradingClient,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("ALPACA_API_KEY")
        self._secret_key = (
            secret_key if secret_key is not None else os.getenv("ALPACA_SECRET_KEY")
        )
        if client is None:
            if not self._api_key or not self._secret_key:
                raise PaperBrokerError(
                    "ALPACA_API_KEY and ALPACA_SECRET_KEY must be configured."
                )
            self._client = client_factory(
                self._api_key,
                self._secret_key,
                paper=True,
                url_override=PAPER_BASE_URL,
            )
        else:
            self._client = client

    def get_account(self) -> dict[str, object]:
        """Return normalized account values from the paper account only."""
        try:
            account = self._client.get_account()
        except Exception as error:
            raise PaperBrokerError("Unable to retrieve Alpaca paper account.") from error
        return {
            "account_id": str(_value(account, "id")),
            "cash": _number(_value(account, "cash"), "cash"),
            "portfolio_value": _number(
                _value(account, "portfolio_value"), "portfolio_value"
            ),
            "buying_power": _number(_value(account, "buying_power"), "buying_power"),
            "paper_trade": True,
        }

    def get_positions(self) -> list[dict[str, object]]:
        """Return normalized open positions from the paper account."""
        try:
            positions = self._client.get_all_positions()
        except Exception as error:
            raise PaperBrokerError("Unable to retrieve Alpaca paper positions.") from error
        return [
            {
                "ticker": str(_value(position, "symbol")),
                "quantity": _number(_value(position, "qty"), "quantity"),
                "market_value": _number(
                    _value(position, "market_value"), "market_value"
                ),
            }
            for position in positions
        ]

    def get_portfolio_state(self) -> PortfolioState:
        """Map Alpaca paper account and positions to FinGraph's source-of-truth state."""
        account = self.get_account()
        total_value = float(account["portfolio_value"])
        positions = {
            str(position["ticker"]): {
                "quantity": float(position["quantity"]),
                "market_value": float(position["market_value"]),
                "position_size": _position_size(
                    float(position["market_value"]), total_value
                ),
            }
            for position in self.get_positions()
        }
        return PortfolioState(
            cash=float(account["cash"]),
            total_value=total_value,
            positions=positions,
        )

    def submit_market_order(
        self, *, ticker: str, action: str, quantity: float
    ) -> ExecutionResult:
        """Submit one market order to the fixed Alpaca paper endpoint."""
        symbol = ticker.strip().upper()
        if not symbol:
            raise ValueError("Ticker must not be empty.")
        if action not in {"BUY", "SELL"}:
            raise ValueError("Paper orders only support BUY or SELL actions.")
        if quantity <= 0:
            raise ValueError("Order quantity must be greater than zero.")

        request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY if action == "BUY" else OrderSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        try:
            order = self._client.submit_order(order_data=request)
        except Exception as error:
            raise PaperBrokerError("Unable to submit Alpaca paper order.") from error
        return self._execution_result(order, action=action, quantity=quantity)

    def get_order_status(
        self, order_id: str, *, action: str, quantity: float
    ) -> ExecutionResult:
        """Retrieve and normalize the latest status of a known paper order."""
        try:
            order = self._client.get_order_by_id(order_id)
        except Exception as error:
            raise PaperBrokerError("Unable to retrieve Alpaca paper order status.") from error
        return self._execution_result(order, action=action, quantity=quantity)

    @staticmethod
    def _execution_result(
        order: Any, *, action: str, quantity: float
    ) -> ExecutionResult:
        """Convert an Alpaca order model into FinGraph's stable schema."""
        return ExecutionResult(
            order_id=str(_value(order, "id")),
            ticker=str(_value(order, "symbol")).upper(),
            action=action,
            quantity=quantity,
            status=_enum_or_text(_value(order, "status")),
            submitted_at=_timestamp(_optional_value(order, "submitted_at")),
            filled_at=_timestamp(_optional_value(order, "filled_at")),
            filled_price=_optional_number(_optional_value(order, "filled_avg_price")),
            paper_trade=True,
        )


def _value(item: Any, field: str) -> Any:
    """Read an Alpaca SDK model or dictionary value with a clear error."""
    if isinstance(item, dict):
        if field not in item:
            raise PaperBrokerError(f"Alpaca response is missing {field}.")
        return item[field]
    try:
        return getattr(item, field)
    except AttributeError as error:
        raise PaperBrokerError(f"Alpaca response is missing {field}.") from error


def _optional_value(item: Any, field: str) -> Any | None:
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)


def _number(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise PaperBrokerError(f"Alpaca {field} is not numeric.") from error


def _optional_number(value: Any) -> float | None:
    if value is None:
        return None
    return _number(value, "filled_avg_price")


def _timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _enum_or_text(value: Any) -> str:
    return str(getattr(value, "value", value))


def _position_size(market_value: float, total_value: float) -> float:
    """Compute account weight safely without inferring a value from an order."""
    if total_value == 0:
        return 0.0
    return market_value / total_value
