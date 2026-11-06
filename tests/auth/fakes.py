"""auth 테스트 공용 fake."""

import uuid
from datetime import datetime, timedelta, timezone

from auth.domain.password_reset_code import PasswordResetCode
from auth.domain.repository.password_reset_code_repository import PasswordResetCodeRepository
from auth.domain.service import Clock

T0 = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


class FakeClock(Clock):
    def __init__(self, now: datetime = T0):
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs) -> None:
        self._now += timedelta(**kwargs)


class FakeCodes(PasswordResetCodeRepository):
    def __init__(self):
        self.rows: dict[uuid.UUID, PasswordResetCode] = {}
        self.saves = 0
        self.deletes = 0

    async def find_by_user_id(self, user_id, for_update=False):
        row = self.rows.get(user_id)
        if row is None:
            return None
        return PasswordResetCode(
            row.user_id, row.code_hash, row.expires_at, row.failed_attempts, row.created_at
        )

    async def save(self, code):
        self.saves += 1
        self.rows[code.user_id] = PasswordResetCode(
            code.user_id, code.code_hash, code.expires_at, code.failed_attempts, code.created_at
        )
        return code

    async def delete(self, user_id):
        self.deletes += 1
        self.rows.pop(user_id, None)
