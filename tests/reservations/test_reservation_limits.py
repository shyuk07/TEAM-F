"""예약 수량·중복 예약 제한 단위 테스트 (DB 없음, R-REQ1·28·29)."""

import uuid

import pytest

from reservations.domain import rules
from reservations.domain.exceptions import PendingReservationExistsError
from reservations.domain.pickup_reservation import PickupReservation
from reservations.domain.pickup_reservation import ReservationStatus as S
from tests.reservations.fakes import build, set_status

pytestmark = pytest.mark.anyio


def test_max_quantity_is_5():
    assert rules.MAX_RESERVATION_QUANTITY == 5
    assert PickupReservation.validate_new_quantity(1) == 1
    assert PickupReservation.validate_new_quantity(5) == 5
    with pytest.raises(ValueError, match="수량은 5개 이하여야 합니다."):
        PickupReservation.validate_new_quantity(6)
    for bad in (0, -1, True, 1.5, "1", None):
        with pytest.raises(ValueError):
            PickupReservation.validate_new_quantity(bad)


async def test_quantity_over_limit_is_rejected_before_stock_is_touched():
    service, _, session, repo, stock, _, log, _ = build()
    before = stock.stock
    log.events.clear()
    with pytest.raises(ValueError):
        await service.create_reservation(uuid.uuid4(), stock.offer_id, 6)
    assert log.events == []  # 할인을 잠그거나 차감하지 않음
    assert stock.stock == before and session.commits == 0 and repo.items == {}


async def test_duplicate_pending_rejected_without_commit():
    service, _, session, repo, stock, *_ = build()
    me = uuid.uuid4()
    await service.create_reservation(me, stock.offer_id, 1)
    commits, items = session.commits, dict(repo.items)
    with pytest.raises(PendingReservationExistsError):
        await service.create_reservation(me, stock.offer_id, 1)
    assert session.commits == commits and repo.items == items  # 저장·commit 없음(차감은 commit 전이라 롤백됨)


@pytest.mark.parametrize("previous", [S.CANCELLED, S.RESERVED, S.PICKED_UP])
async def test_not_pending_previous_reservation_does_not_block(previous):
    service, _, _, _, stock, *_ = build()
    me = uuid.uuid4()
    r = await service.create_reservation(me, stock.offer_id, 1)
    set_status(r, previous)
    again = await service.create_reservation(me, stock.offer_id, 1)
    assert again.status == S.PENDING_PAYMENT


def test_pending_for_other_offer_does_not_block():
    other = PickupReservation.__new__(PickupReservation)
    other.offer_id, other.status = uuid.uuid4(), S.PENDING_PAYMENT
    PickupReservation.ensure_no_pending_for_offer([other], uuid.uuid4())
    with pytest.raises(PendingReservationExistsError):
        PickupReservation.ensure_no_pending_for_offer([other], other.offer_id)
