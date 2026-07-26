"""
In-memory prediction cache with TTL.

Cached predictions expire after CACHE_TTL seconds during market hours,
or persist until end-of-day otherwise. Cache hits skip the entire pipeline.
"""

import time
from datetime import datetime
from typing import Optional
from backend.models import PredictResponse

# 5 minutes during market hours (9:30-16:00 ET), 30 min otherwise
_CACHE_TTL_SHORT = 300
_CACHE_TTL_LONG = 1800

_cache: dict[str, tuple[float, PredictResponse]] = {}


def _ttl() -> int:
    """Return appropriate TTL based on whether markets are open."""
    now = datetime.now()
    # Rough US market hours check (ET = UTC-5/UTC-4)
    hour = now.hour
    # 9:30 ET = ~13:30-14:30 UTC depending on DST
    if 14 <= hour <= 20 and now.weekday() < 5:
        return _CACHE_TTL_SHORT
    return _CACHE_TTL_LONG


def get(symbol: str) -> Optional[PredictResponse]:
    """Get a cached prediction if still fresh."""
    entry = _cache.get(symbol.upper())
    if entry is None:
        return None
    stored_at, result = entry
    if time.time() - stored_at > _ttl():
        del _cache[symbol.upper()]
        return None
    return result


def set(symbol: str, result: PredictResponse) -> None:
    """Store a prediction in cache."""
    _cache[symbol.upper()] = (time.time(), result)


def invalidate(symbol: Optional[str] = None) -> None:
    """Clear cache for a specific symbol or all symbols."""
    if symbol:
        _cache.pop(symbol.upper(), None)
    else:
        _cache.clear()
