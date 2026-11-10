import uuid
from datetime import datetime, timedelta, timezone

import pytest

from reservations.domain import rules
from reservations.domain.exceptions import (
    NotPickupStoreOwnerError,
    NotReservationOwnerError,
    PickupCodeMismatchError,
    ReservationAlreadyCancelledError,
    ReservationAlreadyPickedUpError,
    ReservationConflictError,
    ReservationNotPaidError,
    ReservationStateError,
)
from reservations.domain.offer_ref import OfferRef
from reservations.domain.pickup_reservation import PickupReservation, ReservationStatus

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
S = ReservationStatus


def offer_ref(**kw):
    base = dict(
        offer_id=uuid.uuid4(), owner_id=uuid.uuid4(), store_name="마감 베이커리",
        product_name="샌드위치", pickup_address="서울", sale_price=3000,
        pickup_start=NOW + timedelta(hours=1), pickup_end=NOW + timedelta(hours=3),
    )
    base.update(kw)
    return OfferRef(**base)


def make(status=S.PENDING_PAYMENT, code="A12345"):
    r = PickupReservation.create(uuid.uuid4(), offer_ref(), 2, code, NOW)
    r.status = status
    if status == S.CANCELLED:
        r.cancelled_at = NOW
    if status == S.PICKED_UP:
        r.picked_up_at = NOW
    return r


def test_create_snapshots_and_prices():
    offer = offer_ref()
    uid = uuid.uuid4()
    r = PickupReservation.create(uid, offer, 2, "A12345", NOW)
    assert r.id is None and r.user_id == uid and r.offer_id == offer.offer_id
    assert (r.unit_price, r.total_price, r.quantity) == (3000, 6000, 2)
    assert r.status == S.PENDING_PAYMENT and r.created_at == NOW
    assert (r.store_name, r.product_name, r.pickup_address) == ("마감 베이커리", "샌드위치", "서울")
    assert r.cancelled_at is None and r.picked_up_at is None
    assert r.holds_stock and not r.is_paid


@pytest.mark.parametrize("qty", [0, -1, True, "2"])
def test_create_rejects_bad_quantity(qty):
    with pytest.raises(ValueError):
        PickupReservation.create(uuid.uuid4(), offer_ref(), qty, "A12345", NOW)


def test_create_rejects_naive_now():
    with pytest.raises(ValueError, match="시간대"):
        PickupReservation.create(uuid.uuid4(), offer_ref(), 1, "A12345", datetime(2026, 1, 1))


def test_constructor_validation():
    base = dict(
        user_id=uuid.uuid4(), offer_id=uuid.uuid4(), quantity=2, unit_price=100, total_price=200,
        pickup_code="A1", store_name="s", pickup_address="a", product_name="p",
    )
    PickupReservation(**base)
    with pytest.raises(ValueError, match="총액이 단가×수량과 다릅니다."):
        PickupReservation(**{**base, "total_price": 300})
    with pytest.raises(ValueError):
        PickupReservation(**{**base, "unit_price": -1, "total_price": -2})
    with pytest.raises(ValueError):
        PickupReservation(**{**base, "status": "WHATEVER"})
    with pytest.raises(ValueError):
        PickupReservation(**{**base, "pickup_code": "  "})
    with pytest.raises(ValueError):
        PickupReservation(**{**base, "pickup_code": "X" * 21})
    with pytest.raises(ValueError):
        PickupReservation(**{**base, "store_name": "s" * 151})
    with pytest.raises(ValueError):
        PickupReservation(**{**base, "pickup_address": "a" * 501})
    with pytest.raises(ValueError):
        PickupReservation(**{**base, "product_name": "p" * 201})
    with pytest.raises(ValueError, match="시간대"):
        PickupReservation(**{**base, "created_at": datetime(2026, 1, 1)})
    with pytest.raises(ValueError, match="취소 시각"):
        PickupReservation(**{**base, "cancelled_at": NOW})
    with pytest.raises(ValueError, match="취소 시각"):
        PickupReservation(**{**base, "status": S.CANCELLED})
    with pytest.raises(ValueError, match="픽업 시각"):
        PickupReservation(**{**base, "picked_up_at": NOW})


def test_ensure_owned_by():
    r = make()
    r.ensure_owned_by(r.user_id)
    with pytest.raises(NotReservationOwnerError, match="본인 예약만 취소할 수 있습니다."):
        r.ensure_owned_by(uuid.uuid4())
    assert issubclass(NotReservationOwnerError, PermissionError)


# ── 전이표 전체 ──
def test_mark_paid_table():
    r = make(S.PENDING_PAYMENT)
    r.mark_paid()
    assert r.status == S.RESERVED and r.is_paid
    with pytest.raises(ReservationStateError) as e:
        make(S.RESERVED).mark_paid()
    assert e.value.error_code == "RESERVATION_INVALID_STATE"
    with pytest.raises(ReservationAlreadyCancelledError):
        make(S.CANCELLED).mark_paid()
    with pytest.raises(ReservationAlreadyPickedUpError):
        make(S.PICKED_UP).mark_paid()


@pytest.mark.parametrize("status", [S.PENDING_PAYMENT, S.RESERVED])
def test_cancel_allowed(status):
    r = make(status)
    r.cancel(NOW)
    assert r.status == S.CANCELLED and r.cancelled_at == NOW and not r.holds_stock


def test_cancel_rejected():
    with pytest.raises(ReservationAlreadyCancelledError, match="이미 취소된 예약입니다."):
        make(S.CANCELLED).cancel(NOW)
    with pytest.raises(ReservationAlreadyPickedUpError, match="이미 픽업 완료된 예약입니다."):
        make(S.PICKED_UP).cancel(NOW)
    with pytest.raises(ValueError):
        make().cancel(datetime(2026, 1, 1))


def test_pick_up_ok_and_rejections():
    r = make(S.RESERVED)
    r.pick_up("A12345", NOW)
    assert r.status == S.PICKED_UP and r.picked_up_at == NOW
    with pytest.raises(ReservationNotPaidError, match="결제가 완료되지 않은 예약입니다."):
        make(S.PENDING_PAYMENT).pick_up("A12345", NOW)
    with pytest.raises(ReservationAlreadyCancelledError):
        make(S.CANCELLED).pick_up("A12345", NOW)
    with pytest.raises(ReservationAlreadyPickedUpError):
        make(S.PICKED_UP).pick_up("A12345", NOW)


def test_pick_up_checks_state_before_code():
    # 상태가 종료인 예약에는 코드가 틀려도 409 (D-9)
    with pytest.raises(ReservationAlreadyCancelledError):
        make(S.CANCELLED).pick_up("WRONG", NOW)
    with pytest.raises(ReservationNotPaidError):
        make(S.PENDING_PAYMENT).pick_up("WRONG", NOW)
    r = make(S.RESERVED)
    with pytest.raises(PickupCodeMismatchError, match="예약번호가 일치하지 않습니다.") as e:
        r.pick_up("WRONG", NOW)
    assert e.value.error_code == "PICKUP_CODE_MISMATCH"
    assert r.status == S.RESERVED and r.picked_up_at is None


def test_pickup_code_normalization():
    r = make(S.RESERVED, code="A12345")
    r.pick_up("  a12345 ", NOW)
    assert r.status == S.PICKED_UP


def test_pickup_code_case_sensitive_rule(monkeypatch):
    monkeypatch.setattr(rules, "PICKUP_CODE_CASE_SENSITIVE", True)
    r = make(S.RESERVED, code="A12345")
    with pytest.raises(PickupCodeMismatchError):
        r.pick_up("a12345", NOW)
    r.pick_up("A12345", NOW)


def test_conflict_errors_are_not_value_errors():
    # ValueError면 전역 핸들러가 400으로 바꾼다 (D-16)
    for exc in (ReservationStateError, ReservationAlreadyCancelledError, ReservationNotPaidError):
        assert issubclass(exc, ReservationConflictError) and not issubclass(exc, ValueError)


# ── OfferRef ──
def test_offer_ref_ownership_and_rules(monkeypatch):
    offer = offer_ref()
    offer.ensure_owned_by(offer.owner_id)
    with pytest.raises(NotPickupStoreOwnerError, match="해당 매장의 상점주만 픽업 완료 처리할 수 있습니다."):
        offer.ensure_owned_by(uuid.uuid4())
    # 기본값: 자기 매장 예약 허용, 픽업 시간 강제 없음
    offer.ensure_reservable_by(offer.owner_id)
    offer.ensure_pickup_time(NOW)
    monkeypatch.setattr(rules, "ALLOW_OWNER_SELF_RESERVATION", False)
    monkeypatch.setattr(rules, "PICKUP_WINDOW_ENFORCED", True)
    with pytest.raises(ValueError):
        offer.ensure_reservable_by(offer.owner_id)
    offer.ensure_reservable_by(uuid.uuid4())
    with pytest.raises(ValueError, match="픽업 시간이 아닙니다."):
        offer.ensure_pickup_time(NOW)
    offer.ensure_pickup_time(NOW + timedelta(hours=2))
