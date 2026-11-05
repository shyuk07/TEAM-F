"""예약 API 테스트. DB 없음: 서비스는 fake 레포·세션 + 실제 임시 포트(재고·환불 미연동)로 조립하고,
인증은 get_current_user override로 대체한다."""

import uuid
from typing import Annotated

import httpx
import pytest
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from auth.domain.exceptions import AuthenticationError
from auth.domain.user import Role, User
from auth.presentation.dependencies import bearer_scheme, get_current_user
from main import app
from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.service import ReservationApplicationService
from reservations.domain.offer_ref import OfferRef
from reservations.domain.pickup_reservation import PickupReservation
from reservations.domain.pickup_reservation import ReservationStatus as S
from reservations.infrastructure.payment_refund_stub import NoPaymentRefund
from reservations.presentation.dependencies import provide_reservation_service
from tests.reservations.fakes import NOW, FakeClock, FakeCodes, FakeRepo, FakeSession, Log
from tests.reservations.test_adapters import port

pytestmark = pytest.mark.anyio

CUSTOMER_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()
CREATE_URL = "/v1/reservations"
STOCK_503 = {
    "success": False,
    "error_code": "STOCK_NOT_CONNECTED",
    "message": "재고 연동이 아직 준비되지 않아 예약을 생성할 수 없습니다.",
}
CANCEL_STOCK_503 = {
    "success": False,
    "error_code": "STOCK_NOT_CONNECTED",
    "message": "재고 연동이 아직 준비되지 않아 결제된 예약의 취소·환불을 처리할 수 없습니다.",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def fake_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """토큰 값 "<user_id>:<ROLE>"을 그대로 사용자로 만든다."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("로그인이 필요합니다.")
    user_id, role = credentials.credentials.split(":")
    return User(email="t@example.com", password_hash="x", role=Role(role), id=uuid.UUID(user_id))


@pytest.fixture
def env():
    log = Log()
    session, repo = FakeSession(log), FakeRepo(log)
    stock, offer, owner_id = port()
    lifecycle = ReservationLifecycleService(session=session, reservations=repo, stock=stock, clock=FakeClock())
    service = ReservationApplicationService(
        session=session, lifecycle=lifecycle, reservations=repo, stock=stock,
        refunds=NoPaymentRefund(), clock=FakeClock(), code_generator=FakeCodes(),
    )
    new = {provide_reservation_service: lambda: service, get_current_user: fake_current_user}
    previous = {key: app.dependency_overrides.get(key) for key in new}
    app.dependency_overrides.update(new)
    yield service, session, repo, offer, owner_id
    for key, value in previous.items():
        if value is None:
            app.dependency_overrides.pop(key, None)
        else:
            app.dependency_overrides[key] = value


@pytest.fixture
async def client(env):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


def headers(user_id=CUSTOMER_ID, role="CUSTOMER"):
    return {"Authorization": f"Bearer {user_id}:{role}"}


def err(code, message):
    return {"success": False, "error_code": code, "message": message}


async def add_reservation(env, user_id=CUSTOMER_ID, status=S.PENDING_PAYMENT):
    service, _, repo, offer, _ = env
    terms = await service.stock.get_terms(offer.id)
    reservation = PickupReservation.create(user_id, OfferRef.from_info(terms), 2, "A12345", NOW)
    if status == S.RESERVED:
        reservation.mark_paid()
    await repo.save(reservation)
    return reservation


# ── 생성 ──
async def test_create_requires_login(client, env):
    r = await client.post(CREATE_URL, json={"offer_id": str(env[3].id), "quantity": 1})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"
    assert r.json()["success"] is False


async def test_create_unknown_offer_is_404(client, env):
    env[0].stock.offers.offer = None  # 임시 포트의 fake 레포가 할인을 찾지 못하게 한다
    r = await client.post(CREATE_URL, json={"offer_id": str(uuid.uuid4()), "quantity": 1}, headers=headers())
    assert r.status_code == 404
    assert r.json() == err("NOT_FOUND", "할인 상품을 찾을 수 없습니다.")


async def test_create_out_of_stock_is_409(client, env):
    r = await client.post(CREATE_URL, json={"offer_id": str(env[3].id), "quantity": 99}, headers=headers())
    assert r.status_code == 409
    assert r.json() == err("OUT_OF_STOCK", "재고가 부족합니다.")


async def test_create_not_reservable_is_409(client, env):
    env[3].is_active = False
    r = await client.post(CREATE_URL, json={"offer_id": str(env[3].id), "quantity": 1}, headers=headers())
    assert r.status_code == 409
    assert r.json() == err("OFFER_NOT_RESERVABLE", "예약할 수 없는 상품입니다.")


async def test_create_is_503_and_saves_nothing(client, env):
    _, session, repo, offer, _ = env
    r = await client.post(CREATE_URL, json={"offer_id": str(offer.id), "quantity": 1}, headers=headers())
    assert r.status_code == 503
    assert r.json() == STOCK_503
    assert session.commits == 0 and repo.items == {}
    assert offer.remaining_stock == 3


@pytest.mark.parametrize("quantity", [True, 1.5, "a", "1", 0, -1, None])
async def test_create_quantity_is_strict(client, env, quantity):
    r = await client.post(
        CREATE_URL, json={"offer_id": str(env[3].id), "quantity": quantity}, headers=headers()
    )
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"
    assert env[1].commits == 0


async def test_create_invalid_offer_id_is_400(client, env):
    r = await client.post(CREATE_URL, json={"offer_id": "x", "quantity": 1}, headers=headers())
    assert r.status_code == 400 and r.json()["error_code"] == "VALIDATION_ERROR"


# ── 취소 ──
async def test_cancel_requires_login(client, env):
    r = await client.post(f"/v1/reservations/{uuid.uuid4()}/cancel")
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


async def test_cancel_not_found_is_404(client, env):
    r = await client.post(f"/v1/reservations/{uuid.uuid4()}/cancel", headers=headers())
    assert r.status_code == 404
    assert r.json() == err("NOT_FOUND", "예약 정보를 찾을 수 없습니다.")


async def test_cancel_other_users_reservation_is_403(client, env):
    res = await add_reservation(env)
    r = await client.post(f"/v1/reservations/{res.id}/cancel", headers=headers(OTHER_ID))
    assert r.status_code == 403
    assert r.json() == err("FORBIDDEN", "본인 예약만 취소할 수 있습니다.")


async def test_cancel_unpaid_is_200(client, env):
    res = await add_reservation(env)
    r = await client.post(f"/v1/reservations/{res.id}/cancel", headers=headers())
    assert r.status_code == 200
    assert r.json()["id"] == str(res.id) and r.json()["status"] == "CANCELLED"
    assert env[1].commits == 1


async def test_cancel_twice_is_409(client, env):
    res = await add_reservation(env)
    await client.post(f"/v1/reservations/{res.id}/cancel", headers=headers())
    r = await client.post(f"/v1/reservations/{res.id}/cancel", headers=headers())
    assert r.status_code == 409
    assert r.json() == err("RESERVATION_ALREADY_CANCELLED", "이미 취소된 예약입니다.")


async def test_cancel_paid_is_503_stock_not_connected_and_not_committed(client, env):
    # 임시 재고 포트는 복구하지 못하므로 결제된 예약 취소는 503 (환불 포트까지 가지 않는다)
    res = await add_reservation(env, status=S.RESERVED)
    r = await client.post(f"/v1/reservations/{res.id}/cancel", headers=headers())
    assert r.status_code == 503
    assert r.json() == CANCEL_STOCK_503
    assert env[1].commits == 0  # commit 전에 예외가 올라 DB 변경은 롤백된다
    assert env[3].remaining_stock == 3


async def test_cancel_unpaid_is_200_without_stock_restore(client, env):
    res = await add_reservation(env)
    r = await client.post(f"/v1/reservations/{res.id}/cancel", headers=headers())
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert env[1].commits == 1
    assert env[3].remaining_stock == 3  # 임시 포트: 복구 없이 통과


# ── 목록·픽업 (변경 없음 확인) ──
async def test_list_returns_own_reservations(client, env):
    await add_reservation(env)
    await add_reservation(env, user_id=OTHER_ID)
    r = await client.get("/v1/users/me/reservations", headers=headers())
    assert r.status_code == 200 and r.json()["total"] == 1


async def test_pickup_requires_owner_role(client, env):
    res = await add_reservation(env, status=S.RESERVED)
    body = {"pickup_code": "A12345"}
    r = await client.post(f"/v1/reservations/{res.id}/pickup", json=body)
    assert r.status_code == 401
    r = await client.post(f"/v1/reservations/{res.id}/pickup", json=body, headers=headers())
    assert r.status_code == 403
