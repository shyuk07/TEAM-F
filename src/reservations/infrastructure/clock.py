from datetime import datetime, timezone

from reservations.domain.service import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
