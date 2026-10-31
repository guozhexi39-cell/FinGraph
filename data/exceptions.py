"""Explicit failures raised by the market-data layer."""


class MarketDataError(Exception):
    """Base exception for market-data failures."""


class MarketDataConfigurationError(MarketDataError):
    """Raised when a required provider setting is missing."""


class MarketDataProviderError(MarketDataError):
    """Raised when the upstream provider cannot supply usable data."""


class MarketDataRateLimitError(MarketDataProviderError):
    """Raised when the upstream provider rate-limits a request."""


class MarketDataValidationError(MarketDataError):
    """Raised when provider data violates the FinGraph data contract."""


class FundamentalDataError(MarketDataError):
    """Base exception for fundamental-data failures."""


class FundamentalDataProviderError(FundamentalDataError):
    """Raised when Alpha Vantage cannot provide fundamental data."""


class FundamentalDataValidationError(FundamentalDataError):
    """Raised when fundamental data violates the FinGraph data contract."""


class NewsDataError(MarketDataError):
    """Base exception for company-news failures."""


class NewsDataProviderError(NewsDataError):
    """Raised when Alpha Vantage cannot provide company news."""


class NewsDataValidationError(NewsDataError):
    """Raised when provider news violates the FinGraph data contract."""
