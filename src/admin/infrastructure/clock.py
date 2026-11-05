from datetime import datetime, timezone

from admin.domain.service import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
