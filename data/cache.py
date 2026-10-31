"""Small TTL cache for normalized market-data responses."""

from copy import deepcopy
from dataclasses import dataclass
from time import monotonic
from typing import Callable


@dataclass
class CacheEntry:
    """A cached value and its monotonic expiration time."""

    value: dict[str, object]
    expires_at: float


class MarketDataCache:
    """In-memory ticker cache that expires entries after a configured TTL."""

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._entries: dict[str, CacheEntry] = {}

    def get(self, ticker: str) -> dict[str, object] | None:
        """Return a copy of a non-expired ticker value, if one exists."""
        entry = self._entries.get(ticker)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            del self._entries[ticker]
            return None
        return deepcopy(entry.value)

    def set(self, ticker: str, value: dict[str, object], ttl_seconds: int) -> None:
        """Cache a copy of a normalized response for ``ttl_seconds``."""
        self._entries[ticker] = CacheEntry(
            value=deepcopy(value),
            expires_at=self._clock() + ttl_seconds,
        )


DEFAULT_MARKET_DATA_CACHE = MarketDataCache()
