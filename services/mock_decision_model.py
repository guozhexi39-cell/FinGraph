"""Mock decision model used until a real decision model is introduced."""

from typing import Any

from schemas import TradeProposal


class MockDecisionModel:
    """Build deterministic, schema-validated trade proposals from reports."""

    def propose_trade(
        self,
        ticker: str,
        fundamental_report: Any,
        technical_report: Any,
        news_report: Any,
        portfolio_state: Any,
        risk_result: Any | None,
        risk_retry_count: int,
    ) -> TradeProposal:
        """Return an initial proposal or a position-size-adjusted retry."""
        violations = self._violations(risk_result)

        if risk_retry_count > 0 and "MAX_POSITION_EXCEEDED" in violations:
            return TradeProposal(
                ticker=ticker,
                action="BUY",
                position_size=0.08,
                entry_price=210.0,
                stop_loss=200.0,
                take_profit=230.0,
                confidence=0.72,
                reason="Position size reduced after risk feedback.",
            )

        return TradeProposal(
            ticker=ticker,
            action="BUY",
            position_size=0.15,
            entry_price=210.0,
            stop_loss=200.0,
            take_profit=230.0,
            confidence=0.77,
            reason="Two of the three analyst agents are bullish.",
        )

    @staticmethod
    def _violations(risk_result: Any | None) -> list[str]:
        """Read violations from either a schema instance or state dictionary."""
        if risk_result is None:
            return []
        if isinstance(risk_result, dict):
            return risk_result.get("violations", [])
        return risk_result.violations
