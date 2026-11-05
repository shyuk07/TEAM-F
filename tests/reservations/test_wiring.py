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
    # 임시 구현(호출하면 503). catalog 재고 서비스(C-1)·payments 환불 어댑터(C-4)가 연결되면 이 단언이 실패해 교체를 상기시킨다.
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
