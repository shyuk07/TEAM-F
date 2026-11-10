"""예약 수량·중복 예약 제한 + 실제 PostgreSQL (요구조건 reservations R-REQ1·28·29).

- 수량 1~5, 남은 재고 초과 거절
- 같은 회원·같은 할인의 결제 대기 예약은 1건. 취소하면 재예약, 결제하면 재고가 있는 한 추가 예약
- 상점주가 자기 매장 할인을 예약해도 같은 제한
- 거절된 요청은 예약·재고·재고 기록을 바꾸지 않고, 동시 요청에도 제한이 지켜진다
"""

import asyncio
import uuid

import pytest

from tests.helpers import token_for
from tests.reservations.test_api_db import reserve, seed_offer
from tests.reservations.test_stock_db import cancel, pay, scalar, stock_state

pytestmark = [pytest.mark.db, pytest.mark.anyio]

DUP = {"success": False, "error_code": "PENDING_RESERVATION_EXISTS", "message": "같은 할인 상품에 결제하지 않은 예약이 이미 있습니다."}


async def snapshot(c, offer_id):
    return await stock_state(c, offer_id), await scalar(c, "SELECT count(*) FROM pickup_reservations")


async def test_quantity_bounds_1_to_5(client):
    _, offer_id, _ = await seed_offer(client, stock=20)
    users = [await token_for(client, f"u{i}@test.com") for i in range(2)]
    assert (await reserve(client, users[0], offer_id, 1)).status_code == 201
    assert (await reserve(client, users[1], offer_id, 5)).status_code == 201
    before = await snapshot(client, offer_id)
    over = await token_for(client, "over@test.com")
    for qty in (6, 100):
        r = await reserve(client, over, offer_id, qty)
        assert r.status_code == 400, r.text
        assert r.json() == {"success": False, "error_code": "VALIDATION_ERROR", "message": "수량은 5개 이하여야 합니다."}
    for qty in (0, -1):
        assert (await reserve(client, over, offer_id, qty)).status_code == 400
    assert await snapshot(client, offer_id) == before  # 예약·재고·재고 기록 그대로


async def test_more_than_remaining_within_limit_is_out_of_stock(client):
    _, offer_id, _ = await seed_offer(client, stock=3)
    me = await token_for(client, "me@test.com")
    before = await snapshot(client, offer_id)
    r = await reserve(client, me, offer_id, 4)
    assert r.status_code == 409 and r.json()["error_code"] == "OUT_OF_STOCK"
    assert await snapshot(client, offer_id) == before


async def test_second_pending_for_same_offer_is_rejected_and_changes_nothing(client):
    _, offer_id, _ = await seed_offer(client, stock=10)
    _, other_offer, _ = await seed_offer(client, stock=10, email="owner2@test.com")
    me = await token_for(client, "me@test.com")
    assert (await reserve(client, me, offer_id, 1)).status_code == 201
    before = await snapshot(client, offer_id)
    r = await reserve(client, me, offer_id, 2)
    assert r.status_code == 409 and r.json() == DUP
    assert await snapshot(client, offer_id) == before
    # 다른 할인, 다른 회원은 영향 없음
    assert (await reserve(client, me, other_offer, 1)).status_code == 201
    assert (await reserve(client, await token_for(client, "you@test.com"), offer_id, 1)).status_code == 201


async def test_cancel_then_reserve_again(client):
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 2)).json()["id"]
    assert (await cancel(client, me, rid)).status_code == 200
    r = await reserve(client, me, offer_id, 2)
    assert r.status_code == 201, r.text
    remaining, _, _, total, _ = await stock_state(client, offer_id)
    assert remaining == 8 and total == remaining


async def test_paid_then_additional_reservation_allowed_while_stock_remains(client):
    _, offer_id, _ = await seed_offer(client, stock=6)
    me = await token_for(client, "me@test.com")
    rid = (await reserve(client, me, offer_id, 5)).json()["id"]
    assert (await pay(client, me, rid)).status_code == 201
    r = await reserve(client, me, offer_id, 1)  # 결제 완료 뒤 추가 예약
    assert r.status_code == 201, r.text
    # 새 예약이 결제 대기이므로 다시 막힌다. 재고도 0
    assert (await reserve(client, me, offer_id, 1)).status_code == 409
    remaining, status, _, total, _ = await stock_state(client, offer_id)
    assert (remaining, status, total) == (0, "SOLD_OUT", 0)


async def test_owner_self_reservation_has_same_limits(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    assert (await reserve(client, owner, offer_id, 6)).status_code == 400
    assert (await reserve(client, owner, offer_id, 5)).status_code == 201
    r = await reserve(client, owner, offer_id, 1)
    assert r.status_code == 409 and r.json() == DUP


async def test_concurrent_requests_same_user_same_offer_only_one_succeeds(client):
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    results = await asyncio.gather(*(reserve(client, me, offer_id, 2) for _ in range(5)))
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409, 409, 409, 409], [r.text for r in results]
    assert all(r.json() == DUP for r in results if r.status_code == 409)
    remaining, _, _, total, count = await stock_state(client, offer_id)
    assert remaining == 8 and total == remaining and count == 2  # 최초 입고 + 차감 1건
    assert await scalar(
        client, "SELECT count(*) FROM pickup_reservations WHERE status = 'PENDING_PAYMENT'"
    ) == 1


async def test_concurrent_different_users_are_not_blocked_by_each_other(client):
    _, offer_id, _ = await seed_offer(client, stock=10)
    tokens = [await token_for(client, f"u{i}@test.com") for i in range(4)]
    results = await asyncio.gather(*(reserve(client, t, offer_id, 2) for t in tokens))
    assert [r.status_code for r in results] == [201] * 4
    remaining, _, _, total, _ = await stock_state(client, offer_id)
    assert remaining == 2 and total == remaining


async def test_rejected_duplicate_after_lock_leaves_no_partial_change(client):
    """중복 검사는 할인 잠금·차감 뒤에 일어난다. 거절되면 차감·재고 기록이 남지 않아야 한다."""
    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    assert (await reserve(client, me, offer_id, 1)).status_code == 201
    before = await snapshot(client, offer_id)
    for _ in range(3):
        assert (await reserve(client, me, offer_id, 1)).status_code == 409
    after = await snapshot(client, offer_id)
    assert after == before
    assert uuid.UUID((await reserve(client, await token_for(client, "x@test.com"), offer_id, 1)).json()["id"])


async def test_lock_holder_session_blocks_request_and_request_sees_committed_pending(client):
    """서로 다른 DB 세션·트랜잭션으로 경쟁을 재현한다(타이밍에 기대지 않음).

    세션 A가 할인 행을 FOR UPDATE로 잡고 있는 동안 HTTP 요청 B(별도 세션)는 같은 행 잠금에서 기다려야 한다.
    A가 같은 회원의 결제 대기 예약을 만들고 커밋하면, B는 잠금을 얻은 뒤 그 예약을 보고 409로 거절되며
    B의 차감·재고 기록은 남지 않는다.
    """
    from datetime import datetime, timezone
    from types import SimpleNamespace

    import jwt
    from sqlalchemy import text

    from catalog.infrastructure import models as catalog_models
    from reservations.domain.offer_ref import OfferRef
    from reservations.domain.pickup_reservation import PickupReservation
    from reservations.infrastructure.repositories import SqlAlchemyReservationRepository

    _, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    user_id = uuid.UUID(jwt.decode(me, options={"verify_signature": False})["sub"])
    oid = uuid.UUID(offer_id)

    async with client.session_factory() as a:
        await a.execute(text("SELECT id FROM discount_offers WHERE id = :o FOR UPDATE"), {"o": oid})
        a_pid = (await a.execute(text("SELECT pg_backend_pid()"))).scalar_one()
        b = asyncio.create_task(reserve(client, me, offer_id, 2))
        # 고정 대기 대신, A(pid)에게 막혀 있는 세션이 생길 때까지 확인한다(최대 10초)
        blocked = 0
        for _ in range(100):
            blocked = await scalar(
                client, "SELECT count(*) FROM pg_stat_activity WHERE :p = ANY(pg_blocking_pids(pid))", p=a_pid
            )
            if blocked or b.done():
                break
            await asyncio.sleep(0.1)
        assert blocked == 1, "요청 B가 A의 할인 행 잠금에 막히지 않았다"
        assert not b.done()

        now = datetime.now(timezone.utc)
        ref = OfferRef.from_info(SimpleNamespace(
            offer_id=oid, owner_id=uuid.uuid4(), store_name="마감 베이커리", product_name="샌드위치",
            pickup_address="서울 강남구", sale_price=3000, pickup_start=now, pickup_end=now,
        ))
        await SqlAlchemyReservationRepository(a).save(PickupReservation.create(user_id, ref, 1, "AB3DE9", now))
        await a.execute(
            text("UPDATE discount_offers SET remaining_stock = remaining_stock - 1 WHERE id = :o"), {"o": oid}
        )
        a.add(catalog_models.StockLogModel(offer_id=oid, user_id=user_id, amount=-1, reason="예약 생성"))
        await a.commit()  # 잠금 해제 -> B 진행

    r = await asyncio.wait_for(b, timeout=30)
    assert r.status_code == 409 and r.json() == DUP, r.text
    remaining, _, _, total, count = await stock_state(client, offer_id)
    assert (remaining, total, count) == (9, 9, 2)  # A의 차감만 남음(입고 + A 차감). B 차감은 롤백
    assert await scalar(client, "SELECT count(*) FROM pickup_reservations") == 1
