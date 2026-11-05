"""결제된 예약의 취소·환불은 재고를 복구할 수 없으면 503으로 중단한다 (lifecycle 가드). DB 없음."""

import uuid

import pytest

from reservations.domain.exceptions import StockNotConnectedError
from reservations.domain.pickup_reservation import ReservationStatus as S
from tests.reservations.fakes import FakeStock, build, set_status

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class NoRestoreStock(FakeStock):
    """임시 포트처럼 release가 False(복구 안 함)."""

    async def release(self, offer_id, quantity, *, user_id, reason):
        self.log.events.append("release")
        return False


def env_without_restore():
    service, lifecycle, session, repo, stock, refunds, log, owner = build()
    no_restore = NoRestoreStock(log, owner)
    no_restore.offer_id = stock.offer_id
    lifecycle.stock = no_restore
    service.stock = no_restore
    return service, lifecycle, session, repo, refunds


async def reservation(service, repo, status):
    r = await service.create_reservation(uuid.uuid4(), service.stock.offer_id, 1)
    set_status(r, status)
    repo.items[r.id] = r
    return r


async def test_paid_cancel_without_restore_is_503_and_not_saved():
    service, _, session, repo, refunds = env_without_restore()
    r = await reservation(service, repo, S.RESERVED)
    session.commits = 0

    with pytest.raises(StockNotConnectedError) as e:
        await service.cancel_reservation(r.user_id, r.id)

    assert e.value.error_code == "STOCK_NOT_CONNECTED"
    # RD-38 이후 환불(불일치 확인 포함)이 재고 복구보다 먼저라 환불 포트까지는 간다. 503이 나면 commit 전이라 전부 롤백된다.
    assert session.commits == 0


async def test_unpaid_cancel_without_restore_passes():
    service, _, session, repo, refunds = env_without_restore()
    r = await reservation(service, repo, S.PENDING_PAYMENT)
    session.commits = 0

    out = await service.cancel_reservation(r.user_id, r.id)

    assert out.status == S.CANCELLED and session.commits == 1 and refunds.calls == []


async def test_cancel_for_refund_paid_without_restore_is_503():
    service, lifecycle, session, repo, _ = env_without_restore()
    r = await reservation(service, repo, S.RESERVED)
    session.commits = 0

    with pytest.raises(StockNotConnectedError):
        await lifecycle.cancel_for_refund(r.id, "환불", commit=True)

    assert session.commits == 0


async def test_cancel_for_refund_unpaid_without_restore_passes():
    service, lifecycle, session, repo, _ = env_without_restore()
    r = await reservation(service, repo, S.PENDING_PAYMENT)
    session.commits = 0
    await lifecycle.cancel_for_refund(r.id, "환불", commit=True)
    assert r.status == S.CANCELLED and session.commits == 1


async def test_paid_cancel_with_restore_succeeds():
    service, lifecycle, session, repo, stock, refunds, log, _ = build()
    r = await service.create_reservation(uuid.uuid4(), stock.offer_id, 1)
    set_status(r, S.RESERVED)
    session.commits = 0

    out = await service.cancel_reservation(r.user_id, r.id)

    assert out.status == S.CANCELLED and session.commits == 1 and len(refunds.calls) == 1
