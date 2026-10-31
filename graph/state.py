"""Shared state shape for a future trading workflow."""

from typing import Annotated, Any, TypedDict

from schemas import AnalystReport, ExecutionResult, PortfolioState, RiskResult, TradeProposal


def merge_event_logs(current: list[str], update: list[str]) -> list[str]:
    """Merge sequential and parallel node logs without losing branch events."""
    if not current:
        return update
    if not update:
        return current

    shared_prefix_length = 0
    for current_event, update_event in zip(current, update):
        if current_event != update_event:
            break
        shared_prefix_length += 1
    return [*current, *update[shared_prefix_length:]]


class TradingState(TypedDict, total=False):
    """Data passed between future workflow steps.

    ``total=False`` permits an incrementally populated state as analysis data
    becomes available.
    """

    ticker: str
    market_data: dict[str, Any]
    fundamental_data: dict[str, Any]
    news_data: list[dict[str, Any]]
    portfolio_state: PortfolioState
    fundamental_report: AnalystReport
    technical_report: AnalystReport
    news_report: AnalystReport
    trade_proposal: TradeProposal
    risk_result: RiskResult
    risk_retry_count: int
    human_approval: bool | None
    execution_result: ExecutionResult
    status: str
    run_id: str
    event_log: Annotated[list[str], merge_event_logs]
