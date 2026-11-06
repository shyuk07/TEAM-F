"""회원 탈퇴 연동 DB 통합 테스트 (reservations.md 15.7절). skip은 통과가 아니다 (R16)."""

import uuid

import pytest
from sqlalchemy import text

from auth.infrastructure import models as auth_models  # noqa: F401
from catalog.infrastructure.repositories import SqlAlchemyDiscountOfferRepository
from reservations.domain.pickup_reservation import ReservationStatus as S
from reservations.infrastructure.repositories import SqlAlchemyReservationRepository
from stores.infrastructure import models as stores_models  # noqa: F401
from tests.admin.test_api_db import admin_headers, assert_error, user_id
from tests.helpers import bearer, token_for
from tests.reservations.test_api_db import reserve, seed, seed_offer
from tests.reservations.test_stock_db import pay, scalar, stock_state

pytestmark = [pytest.mark.db, pytest.mark.anyio]


async def withdraw(c, headers, uid, reason="약관 위반"):
    return await c.request("DELETE", f"/v1/admin/users/{uid}", json={"reason": reason}, headers=headers)


async def status_of(c, rid):
    return await scalar(c, "SELECT status FROM pickup_reservations WHERE id = :i", i=uuid.UUID(rid))


async def make_reserved(c, token, offer_id, qty=1):
    r = await reserve(c, token, offer_id, qty)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    p = await pay(c, token, rid)
    assert p.status_code == 201, p.text
    return rid


# ── 탈퇴 흐름 ──
async def test_withdraw_customer_cancels_pending_and_reserved_and_keeps_picked_up(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    me = await token_for(client, "me@test.com")
    uid = str(await user_id(client, "me@test.com"))
    pending = (await reserve(client, me, offer_id, 2)).json()["id"]
    reserved = await make_reserved(client, me, offer_id, 3)
    picked, code = await seed(client, me, offer_id, 1, paid=True)
    await client.post(
        f"/v1/reservations/{picked}/pickup", json={"pickup_code": code}, headers=bearer(owner)
    )
    assert await status_of(client, picked) == "PICKED_UP"
    before_remaining = (await stock_state(client, offer_id))[0]  # 10 - 2 - 3 - 1

    admin = await admin_headers(client)
    r = await withdraw(client, admin, uid)
    assert r.status_code == 200, r.text
    assert r.json()["cancelled_reservation_count"] == 2

    assert await status_of(client, pending) == "CANCELLED"
    assert await status_of(client, reserved) == "CANCELLED"
    assert await status_of(client, picked) == "PICKED_UP"  # 기록 유지
    remaining, _, _, total, _ = await stock_state(client, offer_id)
    assert remaining == before_remaining + 2 + 3 and total == remaining
    async with client.session_factory() as s:
        row = (await s.execute(text("SELECT refund_amount, penalty_amount, status FROM refunds"))).all()
        amount = (
            await s.execute(
                text("SELECT amount FROM payments WHERE reservation_id = :i"), {"i": uuid.UUID(reserved)}
            )
        ).scalar_one()
    assert len(row) == 1 and row[0].penalty_amount == 0 and row[0].refund_amount == amount
    assert await scalar(client, "SELECT status FROM users WHERE id = :i", i=uuid.UUID(uid)) == "WITHDRAWN"


async def test_withdraw_owner_blocked_by_other_customers_reserved_and_rolls_back_all(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    owner_id = str(await user_id(client, "owner@test.com"))
    other = await token_for(client, "other@test.com")
    await make_reserved(client, other, offer_id, 1)
    own = await make_reserved(client, owner, offer_id, 1)  # 점주 본인 예약

    r = await withdraw(client, await admin_headers(client), owner_id)
    assert_error(r, 400, "STORE_HAS_RESERVED_RESERVATIONS")
    assert await status_of(client, own) == "RESERVED"  # 전체 롤백
    assert await scalar(client, "SELECT status FROM users WHERE id = :i", i=uuid.UUID(owner_id)) != "WITHDRAWN"


async def test_withdraw_owner_ignores_own_reserved_and_cancels_it(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    owner_id = str(await user_id(client, "owner@test.com"))
    own = await make_reserved(client, owner, offer_id, 1)  # 본인 예약만 있다
    r = await withdraw(client, await admin_headers(client), owner_id)
    assert r.status_code == 200, r.text
    assert r.json()["cancelled_reservation_count"] == 1
    assert await status_of(client, own) == "CANCELLED"
    assert await scalar(client, "SELECT count(*) FROM refunds") == 1


# ── 정지·탈퇴한 상점주의 픽업 (D-38) ──
async def test_suspended_owner_can_pickup_but_not_reserve_or_cancel_and_withdrawn_gets_401(client):
    owner, offer_id, _ = await seed_offer(client, stock=10)
    owner_id = str(await user_id(client, "owner@test.com"))
    cust = await token_for(client, "c@test.com")
    rid = await make_reserved(client, cust, offer_id, 1)
    code = await scalar(client, "SELECT pickup_code FROM pickup_reservations WHERE id = :i", i=uuid.UUID(rid))
    admin = await admin_headers(client)
    r = await client.patch(
        f"/v1/admin/users/{owner_id}/suspend", json={"reason": "점검", "suspended_until": None}, headers=admin
    )
    assert r.status_code == 200, r.text

    # 정지된 상점주: 생성·취소는 403, 픽업은 200
    assert (await reserve(client, owner, offer_id, 1)).status_code == 403
    assert (await client.post(f"/v1/reservations/{rid}/cancel", headers=bearer(owner))).status_code == 403
    r = await client.post(f"/v1/reservations/{rid}/pickup", json={"pickup_code": code}, headers=bearer(owner))
    assert r.status_code == 200, r.text
    assert await status_of(client, rid) == "PICKED_UP"

    # 정지된 고객도 예약 생성 403
    cust2 = await token_for(client, "c2@test.com")
    c2_id = str(await user_id(client, "c2@test.com"))
    assert (await client.patch(
        f"/v1/admin/users/{c2_id}/suspend", json={"reason": "x", "suspended_until": None}, headers=admin
    )).status_code == 200
    assert (await reserve(client, cust2, offer_id, 1)).status_code == 403

    # 탈퇴한 상점주 토큰은 픽업 401
    rid2 = await make_reserved(client, await token_for(client, "c3@test.com"), offer_id, 1)
    # 매장에 RESERVED가 남아 있으면 탈퇴가 막히므로 먼저 픽업한다
    code2 = await scalar(client, "SELECT pickup_code FROM pickup_reservations WHERE id = :i", i=uuid.UUID(rid2))
    assert (await client.post(
        f"/v1/reservations/{rid2}/pickup", json={"pickup_code": code2}, headers=bearer(owner)
    )).status_code == 200
    assert (await withdraw(client, admin, owner_id)).status_code == 200
    r = await client.post(f"/v1/reservations/{rid2}/pickup", json={"pickup_code": code2}, headers=bearer(owner))
    assert r.status_code == 401, r.text


# ── 실제 레포지토리 ──
async def test_repository_find_by_user_and_statuses_and_exists(client):
    owner, offer_a, store_id = await seed_offer(client, stock=10)
    _, offer_b, other_store = await seed_offer(client, stock=10, email="owner2@test.com")
    me = await token_for(client, "me@test.com")
    uid = uuid.UUID(str(await user_id(client, "me@test.com")))
    rid_p, _ = await seed(client, me, offer_a, 1)
    rid_r, _ = await seed(client, me, offer_b, 1, paid=True)
    rid_done, _ = await seed(client, me, offer_b, 1, paid=True)
    async with client.session_factory() as s:
        await s.execute(
            text("UPDATE pickup_reservations SET status='PICKED_UP' WHERE id = :i"), {"i": uuid.UUID(rid_done)}
        )
        await s.commit()
    async with client.session_factory() as s:
        repo = SqlAlchemyReservationRepository(s)
        found = await repo.find_by_user_and_statuses(uid, [S.PENDING_PAYMENT, S.RESERVED])
        assert {str(r.id) for r in found} == {rid_p, rid_r}  # PICKED_UP 제외
        keys = [(str(r.offer_id), str(r.id)) for r in found]
        assert keys == sorted(keys)  # (offer_id, id) 오름차순
        assert await repo.find_by_user_and_statuses(uid, [S.CANCELLED]) == []
        locked = await repo.find_by_user_and_statuses(uid, [S.RESERVED], for_update=True)
        assert [str(r.id) for r in locked] == [rid_r]

        a, b = uuid.UUID(offer_a), uuid.UUID(offer_b)
        assert await repo.exists_by_offers_and_status([], S.RESERVED) is False
        assert await repo.exists_by_offers_and_status([a], S.RESERVED) is False  # a는 PENDING_PAYMENT만
        assert await repo.exists_by_offers_and_status([a, b], S.RESERVED) is True
        assert await repo.exists_by_offers_and_status([b], S.RESERVED, excluding_user_id=uid) is False
        assert await repo.exists_by_offers_and_status([b], S.RESERVED, excluding_user_id=uuid.uuid4()) is True

        ids_store = await SqlAlchemyDiscountOfferRepository(s).find_ids_by_store(uuid.UUID(store_id))
        ids_other = await SqlAlchemyDiscountOfferRepository(s).find_ids_by_store(
            uuid.UUID(other_store), for_update=True
        )
        assert ids_store == [a] and ids_other == [b]  # 타 상점 제외
        assert await SqlAlchemyDiscountOfferRepository(s).find_ids_by_store(uuid.uuid4()) == []
