"""Mock structured-analysis model used until an LLM integration is needed."""

from typing import Any

from schemas import AnalystReport


class MockAnalystModel:
    """Return deterministic, schema-validated analysis reports.

    The method boundaries mirror the inputs each future LLM-backed analyst
    will receive, so agent nodes do not need redesign when the model changes.
    """

    def analyze_fundamental(
        self, ticker: str, fundamental_data: dict[str, Any]
    ) -> AnalystReport:
        """Produce the fixed fundamental assessment for the supplied ticker."""
        return AnalystReport(
            signal="bullish",
            confidence=0.82,
            evidence=[
                "Revenue growth is positive",
                "Profit growth remains positive",
            ],
            risks=["Debt level is medium"],
            summary="Fundamental condition appears moderately positive.",
        )

    def analyze_technical(self, ticker: str, market_data: dict[str, Any]) -> AnalystReport:
        """Produce the fixed technical assessment for the supplied ticker."""
        return AnalystReport(
            signal="bearish",
            confidence=0.63,
            evidence=["Short-term price movement is unstable"],
            risks=["Volatility remains elevated"],
            summary="Short-term technical conditions are cautious.",
        )

    def analyze_news(self, ticker: str, news_data: list[dict[str, Any]]) -> AnalystReport:
        """Produce the fixed news assessment for the supplied ticker."""
        return AnalystReport(
            signal="bullish",
            confidence=0.74,
            evidence=["Recent news indicates stronger demand"],
            risks=["News sentiment may change rapidly"],
            summary="Recent news flow is moderately positive.",
        )
