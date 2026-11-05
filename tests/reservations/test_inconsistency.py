"""예약 쪽 데이터 불일치(RD-38·RD-39) 도메인·서비스 테스트. DB 없음.

고객 취소(①~④)와 점주 일괄 취소(⑦). 불일치는 DataInconsistentError(500)이고 전부 롤백(commit 0, rollback 1)한다.
ERROR 로그는 서비스에서 요청당 정확히 1건이다(어댑터·라우터는 기록하지 않는다).
"""

import logging
import uuid

import pytest

from reservations.domain.exceptions import (
    DataInconsistentError,
    InconsistencyDetail,
    PickedUpReservationExistsError,
    ReservationAlreadyCancelledError,
    ReservationConflictError,
)
from reservations.domain.pickup_reservation import ReservationStatus as S
from tests.reservations.fakes import build, set_status

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def created(env, user_id=None, status=S.PENDING_PAYMENT, qty=2):
    service, _, _, _, stock, *_ = env
    user_id = user_id or uuid.uuid4()
    r = await service.create_reservation(user_id, stock.offer_id, qty)
    set_status(r, status)
    return r, user_id


def reset(env):
    _, _, session, _, _, _, log, _ = env
    session.commits = session.rollbacks = 0
    log.events.clear()


def error_records(caplog):
    return [r for r in caplog.records if r.levelno >= logging.ERROR]


# ══ 도메인 ══
def test_exception_is_not_any_other_handled_family():
    error = DataInconsistentError([InconsistencyDetail(uuid.uuid4(), "X")])
    for family in (ReservationConflictError, ValueError, PermissionError, LookupError, RuntimeError):
        assert not isinstance(error, family)
    assert error.error_code == "DATA_INCONSISTENT"
    assert str(error) == "예약과 결제 상태가 일치하지 않습니다. 관리자에게 문의해 주세요."
    assert DataInconsistentError().details == () and DataInconsistentError().reservation_ids == ()


async def test_is_pending_payment_property():
    env = build()
    for status, expected in [(S.PENDING_PAYMENT, True), (S.RESERVED, False), (S.CANCELLED, False), (S.PICKED_UP, False)]:
        r, _ = await created(env, status=status, qty=1)
        assert r.is_pending_payment is expected


# ══ 고객 취소 ④ PENDING_PAYMENT + PAID ══
async def test_cancel_pending_with_paid_payment_is_inconsistent_and_writes_nothing(caplog):
    env = build()
    service, _, session, repo, stock, refunds, log, _ = env
    r, uid = await created(env)
    refunds.paid_pending.add(r.id)
    reset(env)
    stock_before = stock.stock

    with caplog.at_level("DEBUG"):
        with pytest.raises(DataInconsistentError) as e:
            await service.cancel_reservation(uid, r.id)

    assert e.value.reservation_ids == (r.id,)
    assert session.commits == 0 and session.rollbacks == 1
    assert r.status == S.PENDING_PAYMENT  # 상태 불변
    assert stock.released == [] and stock.stock == stock_before  # 재고 복구 0
    assert "save" not in log.events and "release" not in log.events  # 예약 저장 0
    assert refunds.calls == []  # 환불 0
    [record] = error_records(caplog)
    text = record.getMessage()
    assert "flow=cancel " in text and f"reservation_id={r.id}" in text and "kind=PAID_PAYMENT_ON_PENDING_RESERVATION" in text


async def test_cancel_pending_without_paid_payment_is_200_and_restores_stock(caplog):
    # 결제 없음/READY/FAILED/REFUNDED는 어댑터(결제 서비스)가 통과시킨다 -> 포트가 정상 반환하면 기존대로 200
    env = build()
    service, _, session, _, stock, refunds, _, _ = env
    r, uid = await created(env)
    reset(env)
    with caplog.at_level("DEBUG"):
        out = await service.cancel_reservation(uid, r.id)
    assert out.status == S.CANCELLED
    assert refunds.calls == [] and refunds.checks == [r.id]  # 환불 호출 0, 확인 1
    assert len(stock.released) == 1 and session.commits == 1 and session.rollbacks == 0
    assert error_records(caplog) == []


# ══ 고객 취소 ①②③ RESERVED + 불일치 ══
async def test_cancel_reserved_with_inconsistent_payment_rolls_back_and_logs_once(caplog):
    env = build()
    service, _, session, _, stock, refunds, log, _ = env
    r, uid = await created(env, status=S.RESERVED)
    refunds.inconsistent.add(r.id)
    reset(env)

    with caplog.at_level("DEBUG"):
        with pytest.raises(DataInconsistentError) as e:
            await service.cancel_reservation(uid, r.id)

    assert e.value.reservation_ids == (r.id,)
    assert session.commits == 0 and session.rollbacks == 1
    assert log.events[-1] == "rollback" and "commit" not in log.events
    assert refunds.calls == []  # 새 환불 0
    assert refunds.checks == []  # RESERVED 취소는 확인 메서드를 부르지 않는다
    assert r.status == S.RESERVED  # 예약 상태 불변(환불 확인이 취소보다 먼저)
    assert stock.released == [] and "save" not in log.events and "release" not in log.events
    [record] = error_records(caplog)
    assert f"reservation_id={r.id}" in record.getMessage() and "kind=PAYMENT_ALREADY_REFUNDED" in record.getMessage()


async def test_cancel_reserved_normal_does_not_call_check():
    env = build()
    service, _, session, _, stock, refunds, _, _ = env
    r, uid = await created(env, status=S.RESERVED)
    reset(env)
    out = await service.cancel_reservation(uid, r.id)
    assert out.status == S.CANCELLED and session.commits == 1 and session.rollbacks == 0
    assert len(refunds.calls) == 1 and refunds.checks == []
    assert len(stock.released) == 1


async def test_recancel_is_409_and_does_not_check_or_log(caplog):
    env = build()
    service, _, session, _, stock, refunds, _, _ = env
    r, uid = await created(env, status=S.CANCELLED)
    refunds.paid_pending.add(r.id)
    with caplog.at_level("DEBUG"):
        with pytest.raises(ReservationAlreadyCancelledError):
            await service.cancel_reservation(uid, r.id)
    assert refunds.checks == [] and error_records(caplog) == []


# ══ ⑦ 점주 일괄 취소 ══
async def test_bulk_cancel_all_normal_commits_nothing_itself(caplog):
    env = build()
    service, _, session, _, stock, refunds, _, _ = env
    r1, _ = await created(env, status=S.RESERVED, qty=1)
    r2, _ = await created(env, status=S.RESERVED, qty=1)
    r3, _ = await created(env, qty=1)  # PENDING_PAYMENT, 결제 없음
    reset(env)
    with caplog.at_level("DEBUG"):
        count = await service.cancel_all_for_offer(stock.offer_id, reason="중단")
    assert count == 3 and len(refunds.calls) == 2 and refunds.checks == [r3.id]
    assert all(call[2] is True for call in refunds.calls)  # waive_penalty
    assert session.commits == 0 and session.rollbacks == 0
    assert error_records(caplog) == []


async def test_bulk_cancel_stops_everything_when_one_is_inconsistent(caplog):
    env = build()
    service, _, session, _, stock, refunds, _, _ = env
    good1, _ = await created(env, status=S.RESERVED, qty=1)
    bad, _ = await created(env, status=S.RESERVED, qty=1)
    good2, _ = await created(env, qty=1)
    refunds.inconsistent.add(bad.id)
    reset(env)

    with caplog.at_level("DEBUG"):
        with pytest.raises(DataInconsistentError) as e:
            await service.cancel_all_for_offer(stock.offer_id, reason="중단")

    assert e.value.reservation_ids == (bad.id,)
    assert str(bad.id) not in str(e.value)  # 메시지에 ID 없음
    assert session.commits == 0 and session.rollbacks == 1
    assert len(error_records(caplog)) == 1


async def test_bulk_cancel_collects_all_inconsistent_ids_in_one_log(caplog):
    env = build()
    service, _, session, _, stock, refunds, _, _ = env
    bad_reserved, _ = await created(env, status=S.RESERVED, qty=1)  # ①②③ 계열
    bad_pending, _ = await created(env, qty=1)  # ④
    await created(env, status=S.RESERVED, qty=1)
    refunds.inconsistent.add(bad_reserved.id)
    refunds.paid_pending.add(bad_pending.id)
    reset(env)

    with caplog.at_level("DEBUG"):
        with pytest.raises(DataInconsistentError) as e:
            await service.cancel_all_for_offer(stock.offer_id, reason="중단")

    assert set(e.value.reservation_ids) == {bad_reserved.id, bad_pending.id}  # 한 건에서 멈추지 않음
    assert session.commits == 0 and session.rollbacks == 1
    [record] = error_records(caplog)  # 요청당 1건, 두 ID 모두 포함
    text = record.getMessage()
    assert str(bad_reserved.id) in text and str(bad_pending.id) in text and "count=2" in text
    assert "@" not in text


async def test_bulk_cancel_picked_up_check_comes_before_inconsistency(caplog):
    env = build()
    service, _, session, _, stock, refunds, log, _ = env
    picked, _ = await created(env, status=S.PICKED_UP, qty=1)
    bad, _ = await created(env, status=S.RESERVED, qty=1)
    refunds.inconsistent.add(bad.id)
    reset(env)
    with caplog.at_level("DEBUG"):
        with pytest.raises(PickedUpReservationExistsError):
            await service.cancel_all_for_offer(stock.offer_id, reason="중단")
    assert refunds.calls == [] and refunds.checks == []
    assert bad.status == S.RESERVED  # 아무것도 바뀌지 않음
    assert error_records(caplog) == []


async def test_bulk_cancel_skips_already_cancelled_without_check():
    env = build()
    service, _, session, _, stock, refunds, _, _ = env
    cancelled, _ = await created(env, status=S.CANCELLED)
    refunds.paid_pending.add(cancelled.id)
    reset(env)
    assert await service.cancel_all_for_offer(stock.offer_id, reason="중단") == 0
    assert refunds.checks == []
