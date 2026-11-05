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
from payments.application.service import PaymentApplicationService
from payments.domain.rules import RESERVATION_PAID_STATUS
from payments.presentation.dependencies import provide_payment_service
from tests.payments.fakes import (
    FakeGateway,
    FakePaymentRepository,
    FakeRefundRepository,
    FakeReservationPort,
    FakeSession,
    FixedClock,
)

pytestmark = pytest.mark.anyio

CUSTOMER_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()
OWNER_ID = uuid.uuid4()
ADMIN_ID = uuid.uuid4()


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def fake_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """실제 인증 의존성 대신 쓰는 가짜. 토큰 값 "<user_id>:<ROLE>"을 그대로 사용자로 만든다."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("로그인이 필요합니다.")
    user_id, role = credentials.credentials.split(":")
    return User(
        email="t@example.com", password_hash="x", role=Role(role), id=uuid.UUID(user_id)
    )


@pytest.fixture
def service():
    service = PaymentApplicationService(
        FakeSession(),
        reservations=FakeReservationPort(),
        payments=FakePaymentRepository(),
        refunds=FakeRefundRepository(),
        gateway=FakeGateway(),
        clock=FixedClock(),
    )
    # 자기가 넣은 키만 넣었다가 원래 값으로 되돌린다 (clear() 금지: container 매핑까지 지워진다).
    new = {provide_payment_service: lambda: service, get_current_user: fake_current_user}
    previous = {key: app.dependency_overrides.get(key) for key in new}
    app.dependency_overrides.update(new)
    yield service
    for key, value in previous.items():
        if value is None:
            app.dependency_overrides.pop(key, None)
        else:
            app.dependency_overrides[key] = value


@pytest.fixture
async def client(service):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


def headers(user_id, role="CUSTOMER"):
    return {"Authorization": f"Bearer {user_id}:{role}"}


async def pay(client, reservation_id, user_id=CUSTOMER_ID, role="CUSTOMER"):
    return await client.post(
        "/v1/payments",
        json={"reservation_id": str(reservation_id)},
        headers=headers(user_id, role),
    )


def error(code, message):
    return {"success": False, "error_code": code, "message": message}


# ---------- 모의 결제 실행 ----------
async def test_pay_success_uses_reservation_price(client, service):
    reservation_id = service.reservations.add(CUSTOMER_ID, total_price=15000)

    response = await pay(client, reservation_id)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "reservation_id", "amount", "status", "paid_at"}
    assert body["reservation_id"] == str(reservation_id)
    assert body["amount"] == 15000
    assert body["status"] == "PAID"
    assert body["paid_at"] is not None
    assert service.reservations.items[reservation_id].status == RESERVATION_PAID_STATUS


@pytest.mark.parametrize("role", ["CUSTOMER", "OWNER", "ADMIN"])
async def test_pay_has_no_role_restriction(client, service, role):
    # 로그인한 회원이면 역할과 상관없이 본인 예약은 결제할 수 있다.
    reservation_id = service.reservations.add(OWNER_ID)
    assert (await pay(client, reservation_id, OWNER_ID, role)).status_code == 201


async def test_pay_without_login_is_401(client, service):
    reservation_id = service.reservations.add(CUSTOMER_ID)

    response = await client.post("/v1/payments", json={"reservation_id": str(reservation_id)})

    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"
    assert response.headers["www-authenticate"] == "Bearer"


async def test_pay_other_users_reservation_is_403(client, service):
    reservation_id = service.reservations.add(CUSTOMER_ID)

    response = await pay(client, reservation_id, OTHER_ID)

    assert response.status_code == 403
    assert response.json() == error("FORBIDDEN", "본인 예약만 결제할 수 있습니다.")


async def test_pay_missing_reservation_is_404(client):
    response = await pay(client, uuid.uuid4())

    assert response.status_code == 404
    assert response.json() == error("NOT_FOUND", "예약 정보를 찾을 수 없습니다.")


async def test_pay_not_payable_reservation_is_400(client, service):
    reservation_id = service.reservations.add(CUSTOMER_ID, status="CANCELLED")

    response = await pay(client, reservation_id)

    assert response.status_code == 400
    assert response.json() == error("RESERVATION_NOT_PAYABLE", "결제할 수 없는 예약입니다.")


async def test_pay_twice_is_409_not_400(client, service):
    # 결제 후 예약 상태가 바뀌어도 중복 결제는 400이 아니라 409
    reservation_id = service.reservations.add(CUSTOMER_ID)
    assert (await pay(client, reservation_id)).status_code == 201

    response = await pay(client, reservation_id)

    assert response.status_code == 409
    # 409는 router가 HTTPException으로 바꾸므로 전역 http_error 핸들러의 코드(CONFLICT)가 나간다.
    assert response.json() == error("CONFLICT", "이미 결제된 예약입니다.")


async def test_pay_invalid_body_is_400_validation_error(client):
    response = await client.post(
        "/v1/payments", json={"reservation_id": "not-a-uuid"}, headers=headers(CUSTOMER_ID)
    )

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert response.json()["error_code"] == "VALIDATION_ERROR"


# ---------- 결제 조회 ----------
async def test_get_payment_owner_only(client, service):
    payment_id = (await pay(client, service.reservations.add(CUSTOMER_ID))).json()["id"]
    url = f"/v1/payments/{payment_id}"

    own = await client.get(url, headers=headers(CUSTOMER_ID))
    assert own.status_code == 200
    assert set(own.json()) == {"id", "reservation_id", "amount", "status", "paid_at"}
    assert own.json()["id"] == payment_id and own.json()["status"] == "PAID"

    # 타인, 상점주, 관리자 모두 403 (본인만, D-4)
    for user_id, role in ((OTHER_ID, "CUSTOMER"), (OWNER_ID, "OWNER"), (ADMIN_ID, "ADMIN")):
        denied = await client.get(url, headers=headers(user_id, role))
        assert denied.status_code == 403
        assert denied.json() == error("FORBIDDEN", "결제 정보를 조회할 권한이 없습니다.")


async def test_get_payment_missing_is_404(client):
    response = await client.get(f"/v1/payments/{uuid.uuid4()}", headers=headers(CUSTOMER_ID))

    assert response.status_code == 404
    assert response.json() == error("NOT_FOUND", "결제 정보를 찾을 수 없습니다.")


async def test_get_payment_without_login_is_401(client):
    response = await client.get(f"/v1/payments/{uuid.uuid4()}")

    assert response.status_code == 401


async def test_get_payment_invalid_uuid_is_400(client):
    response = await client.get("/v1/payments/not-a-uuid", headers=headers(CUSTOMER_ID))

    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"


# ---------- 환불 조회 (서비스로 환불을 만들어 둔다) ----------
async def make_refund(client, service, total_price=12000):
    payment_id = (
        await pay(client, service.reservations.add(CUSTOMER_ID, total_price=total_price))
    ).json()["id"]
    refund = await service.refund(CUSTOMER_ID, uuid.UUID(payment_id), "단순 변심")
    return payment_id, refund


async def test_get_refund_owner_only(client, service):
    payment_id, refund = await make_refund(client, service)
    url = f"/v1/refunds/{refund.id}"

    response = await client.get(url, headers=headers(CUSTOMER_ID))

    assert response.status_code == 200
    assert response.json() == {
        "id": str(refund.id),
        "payment_id": payment_id,
        "refund_amount": 12000,
        "penalty_amount": 0,
        "status": "COMPLETED",
        "completed_at": response.json()["completed_at"],
    }
    assert response.json()["completed_at"] is not None

    for user_id, role in ((OTHER_ID, "CUSTOMER"), (OWNER_ID, "OWNER"), (ADMIN_ID, "ADMIN")):
        denied = await client.get(url, headers=headers(user_id, role))
        assert denied.status_code == 403
        assert denied.json() == error("FORBIDDEN", "환불 정보를 조회할 권한이 없습니다.")


async def test_payment_status_is_refunded_after_refund(client, service):
    payment_id, _ = await make_refund(client, service)

    response = await client.get(f"/v1/payments/{payment_id}", headers=headers(CUSTOMER_ID))

    assert response.json()["status"] == "REFUNDED"


async def test_get_refund_missing_is_404(client):
    response = await client.get(f"/v1/refunds/{uuid.uuid4()}", headers=headers(CUSTOMER_ID))

    assert response.status_code == 404
    assert response.json() == error("NOT_FOUND", "환불 정보를 찾을 수 없습니다.")


async def test_get_refund_without_login_is_401(client):
    assert (await client.get(f"/v1/refunds/{uuid.uuid4()}")).status_code == 401


# ---------- 환불 요청 ----------
async def refund_post(client, payment_id, reason="단순 변심", user_id=CUSTOMER_ID, role="CUSTOMER"):
    return await client.post(
        f"/v1/payments/{payment_id}/refunds",
        json={"reason": reason},
        headers=headers(user_id, role),
    )


async def paid(client, service, total_price=12000):
    reservation_id = service.reservations.add(CUSTOMER_ID, total_price=total_price)
    return (await pay(client, reservation_id)).json()["id"]


async def test_refund_success_response_has_no_completed_at_or_reason(client, service):
    payment_id = await paid(client, service)

    response = await refund_post(client, payment_id)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "payment_id", "refund_amount", "penalty_amount", "status"}
    assert body["payment_id"] == payment_id
    assert body["refund_amount"] == 12000 and body["penalty_amount"] == 0
    assert body["status"] == "COMPLETED"
    after = await client.get(f"/v1/payments/{payment_id}", headers=headers(CUSTOMER_ID))
    assert after.json()["status"] == "REFUNDED"


async def test_refund_without_login_is_401(client, service):
    response = await client.post(f"/v1/payments/{uuid.uuid4()}/refunds", json={"reason": "x"})

    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"


async def test_refund_other_user_is_403(client, service):
    payment_id = await paid(client, service)

    response = await refund_post(client, payment_id, user_id=OTHER_ID)

    assert response.status_code == 403
    assert response.json() == error("FORBIDDEN", "환불을 처리할 권한이 없습니다.")


async def test_refund_missing_payment_is_404(client):
    response = await refund_post(client, uuid.uuid4())

    assert response.status_code == 404
    assert response.json() == error("NOT_FOUND", "결제 정보를 찾을 수 없습니다.")


async def test_refund_twice_is_409(client, service):
    payment_id = await paid(client, service)
    assert (await refund_post(client, payment_id)).status_code == 201

    response = await refund_post(client, payment_id)

    assert response.status_code == 409
    assert response.json()["success"] is False
    assert response.json()["error_code"] == "CONFLICT"


async def test_refund_not_refundable_reservation_state_is_400(client, service):
    payment_id = await paid(client, service)
    reservation_id = next(iter(service.reservations.items))
    service.reservations.set_status(reservation_id, "PICKED_UP")  # CANCELLED는 데이터 불일치(500, RD-38)

    response = await refund_post(client, payment_id)

    assert response.status_code == 400
    assert response.json()["success"] is False


@pytest.mark.parametrize("reason", ["", "가" * 201])
async def test_refund_invalid_reason_is_400(client, service, reason):
    payment_id = await paid(client, service)

    response = await refund_post(client, payment_id, reason=reason)

    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"


async def test_refund_reason_200_chars_ok(client, service):
    payment_id = await paid(client, service)
    assert (await refund_post(client, payment_id, reason="가" * 200)).status_code == 201
