"""관리자 정지·강제 폐점 도메인 규칙 (docs/design/admin.md 3.2)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from stores.domain.exceptions import (
    StoreAlreadyClosedError,
    StoreAlreadySuspendedError,
    StoreClosedError,
    StoreHasReservedReservationsError,
    StoreSuspendedError,
)
from stores.domain.store import Store, StoreStatus
from tests.fakes import DEFAULT_COORDINATES as COORDS

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
OWNER = uuid.uuid4()


def opened():
    return Store.open(OWNER, "상호", "주소", NOW, COORDS)


def test_status_derivation():
    s = opened()
    assert s.status == StoreStatus.ACTIVE
    s.suspend("사유", NOW)
    assert s.status == StoreStatus.SUSPENDED
    s.force_close("폐점", NOW, False)
    assert s.status == StoreStatus.CLOSED


def test_suspend_ok_trims():
    s = opened()
    s.suspend("  위반  ", NOW)
    assert s.suspended_reason == "위반" and s.suspended_at == NOW


@pytest.mark.parametrize("reason", ["", "   ", None])
def test_suspend_blank_reason(reason):
    with pytest.raises(ValueError, match="정지 사유를 입력해 주세요."):
        opened().suspend(reason, NOW)


def test_suspend_reason_too_long():
    with pytest.raises(ValueError, match="사유는 500자 이하여야 합니다."):
        opened().suspend("a" * 501, NOW)


def test_suspend_closed_has_priority_over_already_suspended():
    s = opened()
    s.suspend("x", NOW)
    s.force_close("y", NOW, False)
    with pytest.raises(StoreClosedError, match="폐점된 상점입니다."):
        s.suspend("z", NOW)


def test_suspend_twice():
    s = opened()
    s.suspend("x", NOW)
    with pytest.raises(StoreAlreadySuspendedError, match="이미 정지된 상점입니다."):
        s.suspend("y", NOW)


def test_suspend_naive_now():
    with pytest.raises(ValueError, match="시간대"):
        opened().suspend("x", datetime(2026, 11, 5))


def test_suspend_if_active():
    s = opened()
    assert s.suspend_if_active("x", NOW) is True
    assert s.suspend_if_active("x", NOW) is False
    c = opened()
    c.force_close("y", NOW, False)
    assert c.suspend_if_active("x", NOW) is False
    assert c.suspended_at is None


def test_suspend_if_active_validates_reason():
    with pytest.raises(ValueError, match="정지 사유를 입력해 주세요."):
        opened().suspend_if_active("", NOW)


def test_ensure_force_closable_order():
    s = opened()
    with pytest.raises(ValueError, match="폐점 사유를 입력해 주세요."):
        s.ensure_force_closable(" ")
    s.ensure_force_closable("ok")
    assert s.closed_at is None
    s.force_close("ok", NOW, False)
    with pytest.raises(StoreAlreadyClosedError):
        s.ensure_force_closable("ok")
    with pytest.raises(ValueError, match="폐점 사유를 입력해 주세요."):
        s.ensure_force_closable("")


def test_force_close_ok_even_if_suspended():
    s = opened()
    s.suspend("x", NOW)
    s.force_close(" 사유 ", NOW + timedelta(hours=1), False)
    assert s.closed_at == NOW + timedelta(hours=1) and s.closed_reason == "사유"


def test_force_close_reserved_blocks():
    s = opened()
    with pytest.raises(StoreHasReservedReservationsError):
        s.force_close("x", NOW, True)
    assert s.closed_at is None


def test_force_close_error_order():
    s = opened()
    with pytest.raises(ValueError, match="폐점 사유"):
        s.force_close("", NOW, True)
    s.force_close("x", NOW, False)
    with pytest.raises(StoreAlreadyClosedError):
        s.force_close("x", NOW, True)


def test_force_close_unapproved_after_reserved_check():
    s = Store(owner_id=OWNER, name="상호", pickup_address="주소")
    with pytest.raises(StoreHasReservedReservationsError):
        s.force_close("x", NOW, True)
    with pytest.raises(ValueError, match="승인되지 않은 상점은 폐점할 수 없습니다."):
        s.force_close("x", NOW, False)


def test_force_close_before_approval():
    with pytest.raises(ValueError, match="폐점 시각은 승인 시각 이후여야 합니다."):
        opened().force_close("x", NOW - timedelta(seconds=1), False)


def test_owner_close_blocked_when_suspended():
    s = opened()
    s.suspend("x", NOW)
    with pytest.raises(StoreSuspendedError, match="관리자에 의해 정지된 상점입니다."):
        s.close(NOW)
    assert s.closed_at is None


def test_owner_close_order_closed_before_suspended():
    s = opened()
    s.suspend("x", NOW)
    s.force_close("y", NOW, False)
    with pytest.raises(StoreAlreadyClosedError):
        s.close(NOW)


def test_owner_close_still_works_when_active():
    s = opened()
    s.close(NOW)
    assert s.closed_at == NOW and s.closed_reason is None


def test_invariants():
    base = dict(owner_id=OWNER, name="상호", pickup_address="주소")
    with pytest.raises(ValueError):
        Store(**base, suspended_reason="x")
    with pytest.raises(ValueError):
        Store(**base, suspended_at=NOW)
    with pytest.raises(ValueError):
        Store(**base, closed_reason="x")
    with pytest.raises(ValueError, match="시간대"):
        Store(**base, suspended_reason="x", suspended_at=datetime(2026, 1, 1))
