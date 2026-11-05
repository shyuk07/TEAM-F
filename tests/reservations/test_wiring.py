import inspect
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from container import (
    create_refund_port,
    create_reservation_lifecycle_service,
    create_reservation_service,
    create_stock_port,
    wire_dependencies,
)
from error_handlers import register_exception_handlers
from main import app
from reservations.application.interim_stock_port import ReadOnlyOfferStockPort
from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.service import ReservationApplicationService
from reservations.domain.exceptions import (
    OfferNotReservableError,
    OutOfStockError,
    ReservationAlreadyCancelledError,
    ReservationNotPaidError,
)
from reservations.infrastructure.payment_refund_stub import NoPaymentRefund
from reservations.presentation import dependencies as deps


def _provides():
    return [
        fn
        for name, fn in inspect.getmembers(deps, inspect.isfunction)
        if name.startswith("provide_") and fn.__module__ == deps.__name__
    ]


def test_all_provides_are_wired():
    provides = _provides()
    assert {f.__name__ for f in provides} == {
        "provide_reservation_service",
        "provide_reservation_lifecycle_service",
    }
    fresh = FastAPI()
    wire_dependencies(fresh)
    for fn in provides:
        assert fn in fresh.dependency_overrides, fn.__name__
        assert fn in app.dependency_overrides, fn.__name__
    assert fresh.dependency_overrides[deps.provide_reservation_service] is create_reservation_service
    assert (
        fresh.dependency_overrides[deps.provide_reservation_lifecycle_service]
        is create_reservation_lifecycle_service
    )


def test_placeholders_raise_when_not_wired():
    with pytest.raises(NotImplementedError):
        deps.provide_reservation_service()
    with pytest.raises(NotImplementedError):
        deps.provide_reservation_lifecycle_service()


def test_interim_implementations_remind_replacement():
    # 재고는 아직 임시 포트(catalog 재고 서비스 C-1 연결 시 교체). 환불 포트의 기본값 create_refund_port는
    # 호출하면 503인 fail-closed 안전망이고, 실제 앱에서는 wire_dependencies가 결제 어댑터로 override한다(아래 테스트).
    assert isinstance(create_refund_port(), NoPaymentRefund)
    stock = create_stock_port(offers=SimpleNamespace(), products=SimpleNamespace(), stores=SimpleNamespace())
    assert isinstance(stock, ReadOnlyOfferStockPort)


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_no_payment_refund_raises_not_connected(anyio_backend):
    from reservations.domain.exceptions import RefundNotConnectedError

    with pytest.raises(RefundNotConnectedError) as e:
        await NoPaymentRefund().refund_for_cancelled_reservation(object(), reason="x")
    assert e.value.error_code == "REFUND_NOT_CONNECTED"


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_no_payment_refund_unpaid_check_is_noop_but_refund_stays_503(anyio_backend):
    """안전망(결제 미연동): 확인 불가 시 미결제 취소(200)를 막지 않는다. 결제된 예약의 환불은 계속 503."""
    from reservations.domain.exceptions import RefundNotConnectedError

    assert await NoPaymentRefund().ensure_no_paid_payment(uuid.uuid4()) is None
    with pytest.raises(RefundNotConnectedError):
        await NoPaymentRefund().refund_for_cancelled_reservation(object(), reason="x")


def test_refund_port_implementations_have_same_methods():
    from reservations.application.adapters import PaymentRefundAdapter
    from reservations.application.ports import RefundPort

    declared = {n for n in vars(RefundPort) if not n.startswith("_")}
    assert declared == {"refund_for_cancelled_reservation", "ensure_no_paid_payment"}
    for impl in (NoPaymentRefund, PaymentRefundAdapter):
        assert declared <= set(dir(impl)), impl


def test_service_constructors_require_all_args():
    with pytest.raises(TypeError):
        ReservationApplicationService()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        ReservationLifecycleService()  # type: ignore[call-arg]


def test_reservation_routes_registered():
    paths = {(m.upper(), p) for p, item in app.openapi()["paths"].items() for m in item}
    for pair in [
        ("POST", "/v1/reservations"),
        ("GET", "/v1/users/me/reservations"),
        ("POST", "/v1/reservations/{reservation_id}/cancel"),
        ("POST", "/v1/reservations/{reservation_id}/pickup"),
    ]:
        assert pair in paths, pair


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_conflict_handler_format(anyio_backend):
    small = FastAPI()
    register_exception_handlers(small)

    @small.get("/c/{kind}")
    async def raise_it(kind: str):
        raise {
            "stock": OutOfStockError(),
            "offer": OfferNotReservableError(),
            "cancelled": ReservationAlreadyCancelledError(),
            "unpaid": ReservationNotPaidError(),
        }[kind]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=small), base_url="http://t") as c:
        for kind, code, msg in [
            ("stock", "OUT_OF_STOCK", "재고가 부족합니다."),
            ("offer", "OFFER_NOT_RESERVABLE", "예약할 수 없는 상품입니다."),
            ("cancelled", "RESERVATION_ALREADY_CANCELLED", "이미 취소된 예약입니다."),
            ("unpaid", "RESERVATION_NOT_PAID", "결제가 완료되지 않은 예약입니다."),
        ]:
            r = await c.get(f"/c/{kind}")
            assert r.status_code == 409
            assert r.json() == {"success": False, "error_code": code, "message": msg}


# ── 결제 연동 조립 (container를 옮기지 않고 override로 교체) ──
def test_refund_port_is_overridden_with_payment_adapter_in_wiring():
    from container import create_reservation_refund_port

    fresh = FastAPI()
    wire_dependencies(fresh)
    assert fresh.dependency_overrides[create_refund_port] is create_reservation_refund_port
    assert app.dependency_overrides[create_refund_port] is create_reservation_refund_port


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_container_graph_resolves_and_shares_session(anyio_backend):
    """중첩 Depends까지 override가 적용되고, 예약·결제·어댑터가 같은 세션·같은 lifecycle을 쓴다. NameError 없음."""
    from fastapi import Depends

    from database import get_db
    from payments.application.service import PaymentApplicationService
    from payments.presentation.dependencies import provide_payment_service
    from reservations.application.adapters import PaymentRefundAdapter, PaymentReservationAdapter

    probe = FastAPI()
    wire_dependencies(probe)
    session = object()
    probe.dependency_overrides[get_db] = lambda: session
    seen = {}

    @probe.get("/probe")
    async def route(
        reservation_service: ReservationApplicationService = Depends(deps.provide_reservation_service),
        payment_service: PaymentApplicationService = Depends(provide_payment_service),
    ):
        seen["reservation"] = reservation_service
        seen["payment"] = payment_service
        return {}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=probe), base_url="http://t") as client:
        assert (await client.get("/probe")).status_code == 200

    reservation_service, payment_service = seen["reservation"], seen["payment"]
    refunds = reservation_service.refunds
    assert isinstance(refunds, PaymentRefundAdapter)  # NoPaymentRefund가 아니다
    # RD-39: 미결제 취소의 PAID 결제 확인이 실제 결제 서비스로 이어진다(안전망 no-op이 아니다)
    assert callable(refunds.ensure_no_paid_payment)
    assert callable(refunds.payments.ensure_no_paid_payment_for_reservation)
    assert isinstance(payment_service.reservations, PaymentReservationAdapter)  # InMemory 스텁이 아니다
    assert isinstance(refunds.payments, PaymentApplicationService)
    assert isinstance(refunds.payments.reservations, PaymentReservationAdapter)
    lifecycle = reservation_service.lifecycle
    assert refunds.payments.reservations.lifecycle is lifecycle  # 같은 lifecycle(같은 요청 캐시)
    for owner in (reservation_service, lifecycle, refunds.payments, payment_service):
        assert owner.session is session  # 한 요청 한 세션 (R13)
