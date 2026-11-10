"""할인 판매 중단(일괄 취소) 중 예약·결제 데이터 불일치 -> catalog 라우터가 500 공통 형식 JSON으로 바꾼다. DB 없음.

실제 경로: catalog 라우터 -> CatalogApplicationService -> OfferReservationCanceller -> 예약 서비스(fake 레포·환불).
로그는 예약 서비스의 1건뿐이고(라우터·catalog 서비스는 남기지 않음), 롤백은 예약 서비스가 하며 catalog commit은 일어나지 않는다.
"""

import logging
import uuid
from typing import Annotated

import httpx
import pytest
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from auth.domain.exceptions import AuthenticationError
from auth.domain.user import Role, User
from auth.presentation.dependencies import bearer_scheme, get_current_user
from catalog.presentation.dependencies import provide_catalog_service
from main import app
from reservations.application.catalog_adapters import OfferReservationCanceller
from reservations.domain.pickup_reservation import ReservationStatus as S
from tests.catalog.test_service import Ctx
from tests.reservations.fakes import build, set_status

pytestmark = pytest.mark.anyio

EXPECTED_500 = {
    "success": False,
    "error_code": "DATA_INCONSISTENT",
    "message": "예약과 결제 상태가 일치하지 않습니다. 관리자에게 문의해 주세요.",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def fake_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("로그인이 필요합니다.")
    user_id, role = credentials.credentials.split(":")
    return User(email="t@example.com", password_hash="x", role=Role(role), id=uuid.UUID(user_id))


@pytest.fixture
async def env():
    ctx = Ctx()
    reservation_service, _, res_session, _, stock, refunds, _, _ = build()
    ctx.service.reservation_cancel = OfferReservationCanceller(reservation_service)
    product = await ctx.product()
    offer = await ctx.service.register_offer(ctx.owner, product.id, ctx.offer_data())
    stock.offer_id = offer.offer.id  # 예약 쪽 fake 재고가 같은 할인을 가리키게 한다
    ctx.session.commits = 0

    new = {provide_catalog_service: lambda: ctx.service, get_current_user: fake_current_user}
    previous = {key: app.dependency_overrides.get(key) for key in new}
    app.dependency_overrides.update(new)
    yield ctx, offer.offer, reservation_service, res_session, refunds
    for key, value in previous.items():
        if value is None:
            app.dependency_overrides.pop(key, None)
        else:
            app.dependency_overrides[key] = value


@pytest.fixture
async def client(env):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


def deactivate(client, ctx, offer, cancel=True):
    return client.post(
        f"/v1/offers/{offer.id}/deactivate",
        json={"reason": "재료 소진", "cancel_reservations": cancel},
        headers={"Authorization": f"Bearer {ctx.owner}:OWNER"},
    )


async def test_bulk_cancel_inconsistent_is_500_json_with_single_log_and_no_commit(env, client, caplog):
    ctx, offer, reservation_service, res_session, refunds = env
    r1 = await reservation_service.create_reservation(uuid.uuid4(), reservation_service.stock.offer_id, 1)
    set_status(r1, S.RESERVED)
    refunds.inconsistent.add(r1.id)
    res_session.commits = res_session.rollbacks = 0

    with caplog.at_level(logging.DEBUG):
        r = await deactivate(client, ctx, offer)

    assert r.status_code == 500
    assert r.json() == EXPECTED_500  # 공통 에러 형식, 메시지에 ID 없음
    assert str(r1.id) not in r.text
    assert ctx.session.commits == 0  # catalog commit 없음(할인 중단 롤백)
    assert res_session.commits == 0 and res_session.rollbacks == 1  # 예약 서비스가 롤백
    errors = [x for x in caplog.records if x.levelno >= logging.ERROR]
    assert len(errors) == 1 and errors[0].name == "reservations.application.service"  # 로그는 예약 서비스 1건만
    assert f"reservation_id={r1.id}" in errors[0].getMessage()


async def test_bulk_cancel_normal_path_still_commits_once(env, client):
    ctx, offer, reservation_service, res_session, refunds = env
    r1 = await reservation_service.create_reservation(uuid.uuid4(), reservation_service.stock.offer_id, 1)
    set_status(r1, S.RESERVED)
    res_session.commits = 0
    r = await deactivate(client, ctx, offer)
    assert r.status_code == 200
    assert r.json()["cancelled_reservation_count"] == 1
    assert ctx.session.commits == 1 and res_session.commits == 0  # commit은 catalog 서비스가 1회


async def test_picked_up_reservation_stays_400(env, client):
    ctx, offer, reservation_service, res_session, _ = env
    r1 = await reservation_service.create_reservation(uuid.uuid4(), reservation_service.stock.offer_id, 1)
    set_status(r1, S.PICKED_UP)
    r = await deactivate(client, ctx, offer)
    assert r.status_code == 400 and r.json()["error_code"] == "PICKED_UP_RESERVATION_EXISTS"
    assert ctx.session.commits == 0


async def test_router_without_cancel_reservations_does_not_touch_port(env, client):
    ctx, offer, *_ = env
    r = await deactivate(client, ctx, offer, cancel=False)
    assert r.status_code == 200 and ctx.session.commits == 1
