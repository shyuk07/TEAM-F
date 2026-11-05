"""재고 복구 흐름 테스트 (lifecycle 가드 제거 후). DB 없음.

- 닫힌 할인(release -> False)은 정상 경로다: 결제된 예약도 취소·환불이 성공한다(D40).
- 복구 상한 초과(DataInconsistentError)는 전부 롤백하고 ERROR 로그를 정확히 1건 남긴다.
- 잠금 순서: 할인 -> 예약 -> (결제) -> 환불 -> 재고 복구, commit은 마지막 1회.
"""

import logging
import uuid

import pytest

from reservations.domain.exceptions import DataInconsistentError
from reservations.domain.pickup_reservation import ReservationStatus as S
from tests.reservations.fakes import build, set_status

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def reservation(env, status):
    service, _, _, repo, stock, *_ = env
    r = await service.create_reservation(uuid.uuid4(), stock.offer_id, 1)
    set_status(r, status)
    repo.items[r.id] = r
    return r


def reset(env):
    env[2].commits = env[2].rollbacks = 0
    env[6].events.clear()


async def test_paid_cancel_on_closed_offer_succeeds_without_guard():
    env = build()
    service, lifecycle, session, repo, stock, refunds, log, _ = env
    stock.restore_result = False  # 닫힌 할인: 복구하지 않고 False
    r = await reservation(env, S.RESERVED)
    reset(env)

    out = await service.cancel_reservation(r.user_id, r.id)

    assert out.status == S.CANCELLED and session.commits == 1 and session.rollbacks == 0
    assert len(refunds.calls) == 1 and stock.released == []  # 환불은 하고 재고는 그대로


async def test_cancel_for_refund_paid_on_closed_offer_succeeds():
    env = build()
    _, lifecycle, session, _, stock, *_ = env
    stock.restore_result = False
    r = await reservation(env, S.RESERVED)
    reset(env)
    await lifecycle.cancel_for_refund(r.id, "환불", commit=True)
    assert r.status == S.CANCELLED and session.commits == 1


async def test_unpaid_cancel_on_closed_offer_succeeds():
    env = build()
    service, _, session, _, stock, refunds, *_ = env
    stock.restore_result = False
    r = await reservation(env, S.PENDING_PAYMENT)
    reset(env)
    out = await service.cancel_reservation(r.user_id, r.id)
    assert out.status == S.CANCELLED and session.commits == 1 and refunds.calls == []


async def test_cancel_lock_and_call_order_offer_reservation_refund_release_commit_once():
    env = build()
    service, _, session, _, stock, refunds, log, _ = env
    r = await reservation(env, S.RESERVED)
    reset(env)
    await service.cancel_reservation(r.user_id, r.id)
    events = log.events
    assert events.index("offer_lock") < events.index("res_lock")  # 할인 -> 예약
    assert events.index("res_lock") < events.index("refund") < events.index("release")  # 환불 -> 재고 복구
    assert events.count("commit") == 1 and events[-1] == "commit" and session.commits == 1


async def test_release_over_limit_on_customer_cancel_rolls_back_and_logs_once(caplog):
    env = build()
    service, _, session, _, stock, refunds, log, _ = env
    r = await reservation(env, S.RESERVED)
    stock.over_limit = True
    reset(env)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(DataInconsistentError) as e:
            await service.cancel_reservation(r.user_id, r.id)

    assert e.value.reservation_ids == (r.id,)  # 포트가 모르는 예약 ID를 lifecycle이 채웠다
    assert session.commits == 0 and session.rollbacks == 1
    assert log.events[-1] == "rollback" and "commit" not in log.events
    errors = [x for x in caplog.records if x.levelno >= logging.ERROR]
    assert len(errors) == 1
    assert f"reservation_id={r.id}" in errors[0].getMessage() and "STOCK_RESTORE_OVER_LIMIT" in errors[0].getMessage()


async def test_unpaid_cancel_release_over_limit_also_rolls_back(caplog):
    env = build()
    service, _, session, _, stock, *_ = env
    r = await reservation(env, S.PENDING_PAYMENT)
    stock.over_limit = True
    reset(env)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(DataInconsistentError):
            await service.cancel_reservation(r.user_id, r.id)
    assert session.commits == 0 and session.rollbacks == 1
    assert len([x for x in caplog.records if x.levelno >= logging.ERROR]) == 1


async def test_cancel_for_refund_over_limit_raises_without_logging(caplog):
    # lifecycle은 로그를 남기지 않는다. 기록은 요청을 끝내는 서비스(예약 서비스·결제 서비스)가 1건 한다.
    env = build()
    _, lifecycle, session, _, stock, *_ = env
    r = await reservation(env, S.RESERVED)
    stock.over_limit = True
    reset(env)
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(DataInconsistentError):
            await lifecycle.cancel_for_refund(r.id, "환불", commit=True)
    assert session.commits == 0
    assert [x for x in caplog.records if x.levelno >= logging.ERROR] == []


async def test_bulk_cancel_does_not_restore_stock():
    env = build()
    service, _, session, _, stock, *_ = env
    await reservation(env, S.RESERVED)
    reset(env)
    assert await service.cancel_all_for_offer(stock.offer_id, reason="중단") == 1
    assert stock.released == [] and "release" not in env[6].events  # D40: 일괄 취소는 재고를 복구하지 않는다
    assert session.commits == 0  # 호출한 catalog 서비스가 commit
