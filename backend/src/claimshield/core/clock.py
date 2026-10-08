"""Injectable clock so tests freeze time."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    def __init__(self, instant: datetime) -> None:
        self._instant = instant if instant.tzinfo else instant.replace(tzinfo=UTC)

    def now(self) -> datetime:
        return self._instant


def as_utc(instant: datetime) -> datetime:
    if instant.tzinfo is None:
        return instant.replace(tzinfo=UTC)
    return instant.astimezone(UTC)


def canonical_iso(instant: datetime) -> str:
    return as_utc(instant).replace(microsecond=0).isoformat()
