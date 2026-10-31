"""Deterministic Alpaca paper portfolio synchronization nodes."""

from config import settings
from execution import AlpacaPaperBroker, PaperBrokerError
from graph.state import TradingState
from schemas import PortfolioState


class PortfolioSyncError(RuntimeError):
    """Raised when configured real portfolio synchronization cannot complete."""


def portfolio_sync_node(state: TradingState) -> dict[str, object]:
    """Load the current Alpaca paper account before analyst and decision nodes run."""
    return _sync(state, event="Portfolio state synced from Alpaca Paper")


def portfolio_refresh_node(state: TradingState) -> dict[str, object]:
    """Reload broker state after an approved paper execution attempt."""
    return _sync(state, event="Portfolio state refreshed after paper execution")


def _sync(state: TradingState, *, event: str) -> dict[str, object]:
    if not settings.USE_REAL_PORTFOLIO_STATE:
        return {}
    try:
        portfolio = get_paper_broker().get_portfolio_state()
    except PaperBrokerError as error:
        raise PortfolioSyncError("Unable to synchronize Alpaca paper portfolio state.") from error
    except Exception as error:
        raise PortfolioSyncError("Unable to synchronize Alpaca paper portfolio state.") from error
    if not isinstance(portfolio, PortfolioState):
        raise PortfolioSyncError("Broker returned an invalid PortfolioState.")
    return {
        "portfolio_state": portfolio,
        "event_log": [*state.get("event_log", []), event],
    }


def get_paper_broker() -> AlpacaPaperBroker:
    """Use the existing paper-only broker rather than creating another client type."""
    return AlpacaPaperBroker()
