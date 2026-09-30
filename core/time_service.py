"""UTC wall time for records; monotonic time only for elapsed durations."""

from datetime import datetime, timedelta, timezone
import threading
import time
from typing import Protocol


def as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An aware datetime is required")
    return value.astimezone(timezone.utc)


class Clock(Protocol):
    def now_utc(self) -> datetime: ...
    def monotonic(self) -> float: ...


class SystemClock:
    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic()


class FakeClock:
    def __init__(self, wall_time: datetime):
        self._wall = as_utc(wall_time)
        self._elapsed = 0.0
        self._lock = threading.Lock()

    def now_utc(self) -> datetime:
        with self._lock:
            return self._wall

    def monotonic(self) -> float:
        with self._lock:
            return self._elapsed

    def advance(self, duration: timedelta):
        if not isinstance(duration, timedelta) or duration.total_seconds() < 0:
            raise ValueError("Elapsed time must advance by a nonnegative timedelta")
        with self._lock:
            self._wall += duration
            self._elapsed += duration.total_seconds()

    def set_wall_time(self, value: datetime):
        with self._lock:
            self._wall = as_utc(value)
