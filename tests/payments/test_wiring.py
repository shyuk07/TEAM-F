import inspect

import pytest
from fastapi import FastAPI

from container import (
    create_payment_repository,
    create_payment_reservation_port,
    create_payment_service,
    create_refund_repository,
    wire_dependencies,
)
from main import app
from payments.application.service import PaymentApplicationService
from payments.domain.repository.payment_repository import PaymentRepository
from payments.domain.repository.refund_repository import RefundRepository
from payments.domain.service import Clock, PaymentGateway
from payments.infrastructure.reservation_stub import InMemoryReservationPort
from payments.presentation import dependencies as deps


def test_all_provides_are_wired():
    provides = [
        fn
        for name, fn in inspect.getmembers(deps, inspect.isfunction)
        if name.startswith("provide_") and fn.__module__ == deps.__name__
    ]
    assert [f.__name__ for f in provides] == ["provide_payment_service"]
    fresh = FastAPI()
    wire_dependencies(fresh)
    assert fresh.dependency_overrides[deps.provide_payment_service] is create_payment_service
    assert deps.provide_payment_service in app.dependency_overrides


def test_placeholder_raises_when_not_wired():
    with pytest.raises(NotImplementedError):
        deps.provide_payment_service()


def test_create_payment_service_uses_abstract_implementations():
    reservations = create_payment_reservation_port()
    # 임시 구현. reservations 구현 시 어댑터로 교체하며 이 단언이 실패해 상기시킨다.
    assert isinstance(reservations, InMemoryReservationPort)
    session = object()  # 세션은 쓰이지 않는다(생성만 확인)
    service = create_payment_service(
        session=session,  # type: ignore[arg-type]
        reservations=reservations,
        payments=create_payment_repository(session=session),  # type: ignore[arg-type]
        refunds=create_refund_repository(session=session),  # type: ignore[arg-type]
    )
    assert isinstance(service, PaymentApplicationService)
    assert isinstance(service.payments, PaymentRepository)
    assert isinstance(service.refunds, RefundRepository)
    assert isinstance(service.gateway, PaymentGateway)
    assert isinstance(service.clock, Clock)


def test_payment_routes_registered():
    paths = {
        (method.upper(), path) for path, item in app.openapi()["paths"].items() for method in item
    }
    for m, p in [
        ("POST", "/v1/payments"),
        ("GET", "/v1/payments/{payment_id}"),
        ("POST", "/v1/payments/{payment_id}/refunds"),
        ("GET", "/v1/refunds/{refund_id}"),
    ]:
        assert (m, p) in paths, (m, p)
