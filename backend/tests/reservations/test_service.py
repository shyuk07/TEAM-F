import uuid

import pytest

from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.service import ReservationApplicationService
from reservations.domain.exceptions import (
    NotPickupStoreOwnerError,
    NotReservationOwnerError,
    OfferNotFoundError,
    OutOfStockError,
    PickedUpReservationExistsError,
    PickupCodeMismatchError,
    ReservationAlreadyCancelledError,
    ReservationAlreadyPickedUpError,
    ReservationNotFoundError,
    ReservationNotPaidError,
)
from reservations.domain.pickup_reservation import ReservationStatus as S
from tests.reservations.fakes import build, set_status

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def created(env, user_id=None, qty=2):
    service, _, _, repo, stock, *_ = env
    user_id = user_id or uuid.uuid4()
    r = await service.create_reservation(user_id, stock.offer_id, qty)
    return r, user_id


def test_constructors_require_all_args():
    with pytest.raises(TypeError):
        ReservationApplicationService()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        ReservationLifecycleService()  # type: ignore[call-arg]


# ── 생성 ──
async def test_create_commits_once_and_prices_server_side():
    env = build()
    service, _, session, repo, stock, _, log, _ = env
    r, uid = await created(env)
    assert session.commits == 1
    assert r.id in repo.items and r.user_id == uid and r.status == S.PENDING_PAYMENT
    assert (r.unit_price, r.total_price) == (3000, 6000) and r.pickup_code == "A12345"
    assert stock.stock == 3
    assert log.events[0] == "reserve" and log.events[-1] == "commit"


async def test_create_errors_do_not_commit():
    env = build()
    service, _, session, repo, stock, *_ = env
    with pytest.raises(OfferNotFoundError):
        await service.create_reservation(uuid.uuid4(), uuid.uuid4(), 1)
    stock.stock = 2  # 수량 상한(5) 안에서 재고 부족을 만든다(R-REQ1 이후 99는 수량 검증에서 먼저 막힘)
    with pytest.raises(OutOfStockError):
        await service.create_reservation(uuid.uuid4(), stock.offer_id, 3)
    with pytest.raises(ValueError):
        await service.create_reservation(uuid.uuid4(), stock.offer_id, 0)
    assert session.commits == 0 and repo.items == {}


# ── 목록 ──
async def test_list_only_own_with_filter_and_paging():
    env = build()
    service, _, session, repo, *_ = env
    me = uuid.uuid4()
    for i in range(3):
        r, _ = await created(env, me, 1)
        if i < 2:  # 같은 할인 결제 대기는 1건뿐(R-REQ28): 앞 예약을 취소 상태로 두고 다시 예약
            set_status(r, S.CANCELLED)
    await created(env, uuid.uuid4(), 1)
    commits = session.commits
    page = await service.list_my_reservations(me, None, 1, 2)
    assert (page.total, len(page.items), page.page, page.size) == (3, 2, 1, 2)
    assert all(i.user_id == me for i in page.items)
    set_status(page.items[0], S.RESERVED)
    assert (await service.list_my_reservations(me, S.RESERVED, 1, 20)).total == 1
    assert session.commits == commits  # 읽기 전용


# ── 취소 ──
async def test_cancel_order_restores_stock_and_commits_once():
    env = build()
    service, _, session, repo, stock, refunds, log, _ = env
    r, uid = await created(env)
    log.events.clear()
    session.commits = 0
    out = await service.cancel_reservation(uid, r.id)
    assert out.status == S.CANCELLED and out.cancelled_at is not None
    assert stock.stock == 5 and session.commits == 1
    # 잠금 순서(RD-5): 잠금 없는 읽기 -> (offer 잠금 -> 예약 잠금: 환불 여부 판단) -> (같은 잠금 재진입) -> release -> commit
    assert log.events == [
        "res_read", "offer_read", "res_read", "offer_lock", "res_lock",
        "res_read", "offer_lock", "res_lock", "release", "save", "commit",
    ]
    assert refunds.calls == []  # 결제 전이라 환불 없음


async def test_cancel_forbidden_before_any_lock():
    env = build()
    service, _, session, repo, stock, _, log, _ = env
    r, uid = await created(env)
    log.events.clear()
    with pytest.raises(NotReservationOwnerError, match="본인 예약만 취소할 수 있습니다."):
        await service.cancel_reservation(uuid.uuid4(), r.id)
    assert "offer_lock" not in log.events and "res_lock" not in log.events
    assert stock.stock == 3 and r.status == S.PENDING_PAYMENT


async def test_cancel_not_found():
    service, *_ = build()
    with pytest.raises(ReservationNotFoundError, match="예약 정보를 찾을 수 없습니다."):
        await service.cancel_reservation(uuid.uuid4(), uuid.uuid4())


async def test_double_cancel_does_not_restore_twice():
    env = build()
    service, _, session, _, stock, *_ = env
    r, uid = await created(env)
    await service.cancel_reservation(uid, r.id)
    with pytest.raises(ReservationAlreadyCancelledError):
        await service.cancel_reservation(uid, r.id)
    assert stock.stock == 5 and len(stock.released) == 1


async def test_cancel_picked_up_conflict():
    env = build()
    service, *_ = env
    r, uid = await created(env)
    set_status(r, S.PICKED_UP)
    with pytest.raises(ReservationAlreadyPickedUpError):
        await service.cancel_reservation(uid, r.id)


async def test_cancel_paid_calls_refund_and_failure_means_no_commit():
    env = build()
    service, _, session, _, stock, refunds, _, _ = env
    r, uid = await created(env)
    set_status(r, S.RESERVED)
    session.commits = 0
    await service.cancel_reservation(uid, r.id)
    (target, reason, waive), = refunds.calls
    assert target.reservation_id == r.id and target.total_price == 6000
    assert target.status == "RESERVED" and waive is False and reason == "고객 요청 취소"
    assert session.commits == 1

    r2, uid2 = await created(env)
    set_status(r2, S.RESERVED)
    session.commits = 0
    refunds.fail = True
    with pytest.raises(RuntimeError):
        await service.cancel_reservation(uid2, r2.id)
    assert session.commits == 0


# ── 픽업 ──
async def test_pickup_ok_locks_only_reservation():
    env = build()
    service, _, session, repo, stock, _, log, owner = env
    r, _ = await created(env)
    set_status(r, S.RESERVED)
    log.events.clear()
    session.commits = 0
    out = await service.complete_pickup(owner, r.id, "a12345")
    assert out.status == S.PICKED_UP and out.picked_up_at is not None and session.commits == 1
    assert "offer_lock" not in log.events and "release" not in log.events


async def test_pickup_errors():
    env = build()
    service, _, session, _, _, _, _, owner = env
    r, _ = await created(env)
    with pytest.raises(NotPickupStoreOwnerError):
        await service.complete_pickup(uuid.uuid4(), r.id, "A12345")
    with pytest.raises(ReservationNotFoundError):
        await service.complete_pickup(owner, uuid.uuid4(), "A12345")
    with pytest.raises(ReservationNotPaidError):
        await service.complete_pickup(owner, r.id, "A12345")
    set_status(r, S.RESERVED)
    with pytest.raises(PickupCodeMismatchError):
        await service.complete_pickup(owner, r.id, "ZZZ")
    assert session.commits == 1  # 생성 때의 1회뿐
    set_status(r, S.CANCELLED)
    with pytest.raises(ReservationAlreadyCancelledError):
        await service.complete_pickup(owner, r.id, "A12345")


# ── lifecycle ──
async def test_lifecycle_snapshot_mark_paid_and_cancel_for_refund_idempotent():
    env = build()
    service, lifecycle, session, _, stock, _, _, _ = env
    assert await lifecycle.get_snapshot(uuid.uuid4()) is None
    r, uid = await created(env)
    view = await lifecycle.get_snapshot(r.id, for_update=True)
    assert view.reservation is r and view.offer.offer_id == r.offer_id
    session.commits = 0
    await lifecycle.mark_paid(r.id)
    assert r.status == S.RESERVED and session.commits == 0
    await lifecycle.cancel_for_refund(r.id, "환불")
    assert r.status == S.CANCELLED and stock.stock == 5
    await lifecycle.cancel_for_refund(r.id, "환불")  # 멱등
    assert len(stock.released) == 1 and session.commits == 0
    with pytest.raises(ReservationNotFoundError):
        await lifecycle.cancel_for_refund(uuid.uuid4(), "x")
    r2, _ = await created(env)
    set_status(r2, S.PICKED_UP)
    with pytest.raises(ReservationAlreadyPickedUpError):
        await lifecycle.cancel_for_refund(r2.id, "x")


async def test_lifecycle_commit_flag():
    env = build()
    _, lifecycle, session, *_ = env
    r, uid = await created(env)
    session.commits = 0
    await lifecycle.cancel(r.id, reason="x", actor_user_id=uid, commit=True)
    assert session.commits == 1


# ── 일괄 취소 ──
async def test_cancel_all_for_offer_refunds_paid_only_no_commit_no_stock_restore():
    env = build()
    service, _, session, repo, stock, refunds, _, _ = env
    a, _ = await created(env, qty=1)
    b, _ = await created(env, qty=1)
    c, _ = await created(env, qty=1)
    set_status(b, S.RESERVED)
    set_status(c, S.CANCELLED)
    session.commits = 0
    n = await service.cancel_all_for_offer(stock.offer_id, reason="판매 중단")
    assert n == 2 and session.commits == 0
    assert a.status == S.CANCELLED and b.status == S.CANCELLED
    assert stock.released == []  # D40
    (target, reason, waive), = refunds.calls
    assert target.reservation_id == b.id and waive is True and reason == "판매 중단"


async def test_cancel_all_aborts_without_changes_when_picked_up_exists():
    env = build()
    service, _, session, _, stock, refunds, _, _ = env
    a, _ = await created(env)
    b, _ = await created(env)
    set_status(b, S.PICKED_UP)
    session.commits = 0
    with pytest.raises(PickedUpReservationExistsError):
        await service.cancel_all_for_offer(stock.offer_id, reason="x")
    assert a.status == S.PENDING_PAYMENT and refunds.calls == [] and session.commits == 0
