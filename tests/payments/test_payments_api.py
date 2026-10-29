import asyncio
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from payments.application.ports import ReservationInfo
from payments.application.service import ConflictError, PaymentService
from payments.domain.payment import Payment
from payments.domain.refund import Refund
from payments.presentation.dependencies import get_payment_service


CUSTOMER_ID = uuid4()
OTHER_CUSTOMER_ID = uuid4()
OWNER_ID = uuid4()
ADMIN_ID = uuid4()


# DB 없이 테스트하기 위한 메모리 저장소
class FakePaymentRepository:
    def __init__(self):
        self.payments: dict[UUID, Payment] = {}
        self.refunds: dict[UUID, Refund] = {}

    async def get_payment(self, payment_id):
        return self.payments.get(payment_id)

    async def get_payment_by_reservation(self, reservation_id):
        return next(
            (p for p in self.payments.values() if p.reservation_id == reservation_id),
            None,
        )

    async def add_payment(self, payment):
        self.payments[payment.id] = payment

    async def get_refund(self, refund_id):
        return self.refunds.get(refund_id)

    async def add_refund(self, refund, payment):
        self.refunds[refund.id] = refund
        self.payments[payment.id] = payment


class FakeReservationGateway:
    def __init__(self):
        self.reservations: dict[UUID, ReservationInfo] = {}

    def add(self, total_price=12000, status="PENDING_PAYMENT") -> UUID:
        reservation_id = uuid4()
        self.reservations[reservation_id] = ReservationInfo(
            id=reservation_id,
            user_id=CUSTOMER_ID,
            store_owner_id=OWNER_ID,
            total_price=total_price,
            status=status,
        )
        return reservation_id

    async def get(self, reservation_id):
        return self.reservations.get(reservation_id)

    async def mark_paid(self, reservation_id):
        self.reservations[reservation_id] = ReservationInfo(
            **{**self.reservations[reservation_id].__dict__, "status": "CONFIRMED"}
        )


@pytest.fixture
def service():
    service = PaymentService(FakePaymentRepository(), FakeReservationGateway())
    app.dependency_overrides[get_payment_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def client(service):
    return TestClient(app)


def headers(user_id, role):
    return {"X-User-Id": str(user_id), "X-User-Role": role}


def pay(client, reservation_id, user_id=CUSTOMER_ID, role="CUSTOMER"):
    return client.post(
        "/api/v1/payments",
        json={"reservation_id": str(reservation_id)},
        headers=headers(user_id, role),
    )


# ---------- 모의 결제 실행 ----------

def test_결제_성공시_예약금액으로_PAID(client, service):
    reservation_id = service.reservations.add(total_price=15000)

    response = pay(client, reservation_id)

    assert response.status_code == 201
    body = response.json()
    assert body["reservation_id"] == str(reservation_id)
    assert body["amount"] == 15000
    assert body["status"] == "PAID"
    assert body["paid_at"] is not None
    assert service.reservations.reservations[reservation_id].status == "CONFIRMED"


def test_로그인_안하면_401(client, service):
    reservation_id = service.reservations.add()

    response = client.post("/api/v1/payments", json={"reservation_id": str(reservation_id)})

    assert response.status_code == 401


def test_고객이_아니면_403(client, service):
    reservation_id = service.reservations.add()

    assert pay(client, reservation_id, OWNER_ID, "OWNER").status_code == 403


def test_남의_예약은_403(client, service):
    reservation_id = service.reservations.add()

    assert pay(client, reservation_id, OTHER_CUSTOMER_ID).status_code == 403


def test_없는_예약은_404(client):
    assert pay(client, uuid4()).status_code == 404


def test_결제대기_아닌_예약은_409(client, service):
    reservation_id = service.reservations.add(status="CANCELLED")

    assert pay(client, reservation_id).status_code == 409


def test_중복_결제는_409(client, service):
    reservation_id = service.reservations.add()
    pay(client, reservation_id)

    # 예약 상태와 무관하게 결제 내역이 이미 있으면 막혀야 함
    service.reservations.reservations[reservation_id] = ReservationInfo(
        **{**service.reservations.reservations[reservation_id].__dict__,
           "status": "PENDING_PAYMENT"}
    )
    assert pay(client, reservation_id).status_code == 409


# ---------- 결제 상태 조회 ----------

def test_결제_조회_본인과_관리자만(client, service):
    payment_id = pay(client, service.reservations.add()).json()["id"]
    url = f"/api/v1/payments/{payment_id}"

    assert client.get(url, headers=headers(CUSTOMER_ID, "CUSTOMER")).status_code == 200
    assert client.get(url, headers=headers(ADMIN_ID, "ADMIN")).status_code == 200
    assert client.get(url, headers=headers(OTHER_CUSTOMER_ID, "CUSTOMER")).status_code == 403
    assert client.get(url, headers=headers(OWNER_ID, "OWNER")).status_code == 403


def test_없는_결제_조회는_404(client):
    response = client.get(f"/api/v1/payments/{uuid4()}", headers=headers(CUSTOMER_ID, "CUSTOMER"))

    assert response.status_code == 404


# ---------- 환불 처리 / 환불 조회 ----------

async def _refund(service, payment_id, penalty=2000):
    return await service.refund(UUID(payment_id), penalty_amount=penalty, reason="단순 변심")


def test_환불시_위약금_차감_및_결제_REFUNDED(client, service):

    payment_id = pay(client, service.reservations.add(total_price=12000)).json()["id"]
    refund = asyncio.run(_refund(service, payment_id, penalty=2000))

    assert refund.refund_amount == 10000
    assert refund.penalty_amount == 2000

    payment = client.get(f"/api/v1/payments/{payment_id}", headers=headers(CUSTOMER_ID, "CUSTOMER"))
    assert payment.json()["status"] == "REFUNDED"


def test_위약금이_결제금액보다_크면_거절(client, service):

    payment_id = pay(client, service.reservations.add(total_price=5000)).json()["id"]

    with pytest.raises(ConflictError):
        asyncio.run(_refund(service, payment_id, penalty=6000))


def test_중복_환불_거절(client, service):

    payment_id = pay(client, service.reservations.add()).json()["id"]
    asyncio.run(_refund(service, payment_id))

    with pytest.raises(ConflictError):
        asyncio.run(_refund(service, payment_id))


def test_환불_조회_본인_매장주_관리자만(client, service):

    payment_id = pay(client, service.reservations.add(total_price=12000)).json()["id"]
    refund = asyncio.run(_refund(service, payment_id))
    url = f"/api/v1/refunds/{refund.id}"

    response = client.get(url, headers=headers(CUSTOMER_ID, "CUSTOMER"))
    assert response.status_code == 200
    assert response.json() == {
        "id": str(refund.id),
        "payment_id": payment_id,
        "refund_amount": 10000,
        "penalty_amount": 2000,
        "reason": "단순 변심",
        "status": "COMPLETED",
        "completed_at": response.json()["completed_at"],
    }
    assert client.get(url, headers=headers(OWNER_ID, "OWNER")).status_code == 200
    assert client.get(url, headers=headers(ADMIN_ID, "ADMIN")).status_code == 200
    assert client.get(url, headers=headers(OTHER_CUSTOMER_ID, "CUSTOMER")).status_code == 403
    assert client.get(url, headers=headers(uuid4(), "OWNER")).status_code == 403
