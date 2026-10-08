from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from claimshield.core.errors import RateLimited


class SlidingWindowLimiter:
    def __init__(self, *, limit: int = 5, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window = timedelta(seconds=window_seconds)
        self._hits: dict[str, deque[datetime]] = defaultdict(deque)

    def check(self, key: str, now: datetime | None = None) -> None:
        instant = now or datetime.now(UTC)
        bucket = self._hits[key]
        cutoff = instant - self.window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            raise RateLimited("too many login attempts")
        bucket.append(instant)

    def reset(self) -> None:
        self._hits.clear()
