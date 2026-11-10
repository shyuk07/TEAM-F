"""관리자 강제 탈퇴용 예약 어댑터 단위 테스트 (DB 없음, 사용자 결정 2026-11-10)."""

import uuid

import pytest

from admin.domain.exceptions import ReservationDataInconsistentError
from reservations.application.admin_adapters import AdminWithdrawalReservationAdapter, ReservationAdminAdapter
from reservations.domain import rules
from reservations.domain.exceptions import DataInconsistentError, InconsistencyDetail

pytestmark = pytest.mark.anyio


class FakeService:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    async def cancel_all_for_user(self, user_id, *, reason):
        self.calls.append((user_id, reason))
        if self.error:
            raise self.error
        return 3


class FakeQuery:
    async def has_reserved_for_store(self, store_id, *, excluding_user_id=None):
        return True


async def test_admin_adapter_uses_fixed_reason_instead_of_admin_text():
    service = FakeService()
    adapter = AdminWithdrawalReservationAdapter(service, FakeQuery())
    uid = uuid.uuid4()
    assert await adapter.cancel_active_for_user(uid, reason="가" * 500) == 3
    assert service.calls == [(uid, "관리자 강제 탈퇴")]
    assert rules.ADMIN_WITHDRAWAL_CANCEL_REASON == "관리자 강제 탈퇴" and len(rules.ADMIN_WITHDRAWAL_CANCEL_REASON) <= 200
    assert await adapter.has_reserved_for_store(uuid.uuid4()) is True  # 나머지 동작은 그대로


async def test_self_withdrawal_adapter_keeps_caller_reason():
    service = FakeService()
    uid = uuid.uuid4()
    await ReservationAdminAdapter(service, FakeQuery()).cancel_active_for_user(uid, reason="회원 본인 탈퇴")
    assert service.calls == [(uid, "회원 본인 탈퇴")]


async def test_admin_adapter_still_translates_inconsistency():
    error = DataInconsistentError([InconsistencyDetail(uuid.uuid4(), "X")])
    adapter = AdminWithdrawalReservationAdapter(FakeService(error), FakeQuery())
    with pytest.raises(ReservationDataInconsistentError):
        await adapter.cancel_active_for_user(uuid.uuid4(), reason="x")
