"""
Small in-memory TTL cache for market data, plus the helper that turns a
cache hit / market-hours check into the "Live / Cached / Market Closed"
badge the frontend shows next to each quote.

Market data APIs are slow-ish and rate-limit aggressively on free tiers.
Caching quotes for a short window keeps the app responsive when several
users/tabs hit the same symbol and avoids hammering the upstream
provider. In production this would be swapped for Redis (see
docs/architecture.md's scaling notes) without changing the call sites,
since it exposes the same get/set interface.
"""
import time
from typing import Any, Optional
from threading import Lock

from cachetools import TTLCache


class QuoteCache:
    def __init__(self, maxsize: int = 512, ttl_seconds: int = 60):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value

    def age_seconds(self, key: str, stored_at: float) -> float:
        return time.time() - stored_at


# 60s TTL: long enough that rapid page reloads / multiple watchlist
# widgets on the same page don't each trigger their own upstream call,
# short enough that "Live" data doesn't go stale-looking during market
# hours.
quote_cache = QuoteCache()


def classify_freshness(from_cache: bool, market_open: bool) -> str:
    """Classify a quote for the UI's Live / Cached / Market Closed badge.

    Market-closed takes priority over cache status: there's no such
    thing as a "live" quote outside trading hours, only "last close",
    which we surface as market_closed regardless of whether this
    particular response happened to come from cache.
    """
    if not market_open:
        return "market_closed"
    return "cached" if from_cache else "live"
