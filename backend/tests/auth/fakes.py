"""auth 테스트 공용 fake."""

from datetime import datetime, timedelta, timezone

from auth.domain.service import Clock

T0 = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


class FakeClock(Clock):
    def __init__(self, now: datetime = T0):
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs) -> None:
        self._now += timedelta(**kwargs)
