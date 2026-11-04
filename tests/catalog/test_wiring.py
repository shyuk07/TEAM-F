import inspect

import pytest
from fastapi import FastAPI

from catalog.application.service import CatalogApplicationService
from catalog.presentation import dependencies as deps
from catalog.infrastructure.reservation_cancel import NoReservationCancel
from catalog.infrastructure.reservation_lookup import NoReservationLookup
from container import (
    create_catalog_service,
    create_reservation_cancel,
    create_reservation_lookup,
    create_store_port,
    wire_dependencies,
)
from main import app


def _provides():
    return [
        fn
        for name, fn in inspect.getmembers(deps, inspect.isfunction)
        if name.startswith("provide_") and fn.__module__ == deps.__name__
    ]


def test_all_provides_are_wired():
    provides = _provides()
    assert {f.__name__ for f in provides} == {
        "provide_catalog_service",
        "provide_store_port",
        "provide_reservation_lookup",
        "provide_reservation_cancel",
    }
    fresh = FastAPI()
    wire_dependencies(fresh)
    for fn in provides:
        assert fn in fresh.dependency_overrides, fn.__name__
        assert fn in app.dependency_overrides, fn.__name__
    assert fresh.dependency_overrides[deps.provide_catalog_service] is create_catalog_service
    assert fresh.dependency_overrides[deps.provide_store_port] is create_store_port
    assert fresh.dependency_overrides[deps.provide_reservation_lookup] is create_reservation_lookup
    # 임시 구현. reservations 구현 시 어댑터로 교체하며 이 단언이 실패해 상기시킨다 (CI-10)
    assert isinstance(create_reservation_lookup(), NoReservationLookup)
    assert fresh.dependency_overrides[deps.provide_reservation_cancel] is create_reservation_cancel
    # 임시 구현. reservations 구현 시 어댑터로 교체하며 이 단언이 실패해 상기시킨다 (CI-11)
    assert isinstance(create_reservation_cancel(), NoReservationCancel)


def test_placeholders_raise_when_not_wired():
    with pytest.raises(NotImplementedError):
        deps.provide_catalog_service()
    with pytest.raises(NotImplementedError):
        deps.provide_store_port()
    with pytest.raises(NotImplementedError):
        deps.provide_reservation_lookup()
    with pytest.raises(NotImplementedError):
        deps.provide_reservation_cancel()


def test_catalog_routes_registered():
    paths = {
        (method.upper(), path)
        for path, item in app.openapi()["paths"].items()
        for method in item
    }
    for m, p in [
        ("POST", "/v1/stores/{store_id}/products"),
        ("GET", "/v1/stores/{store_id}/products"),
        ("GET", "/v1/products/{product_id}"),
        ("PATCH", "/v1/products/{product_id}"),
        ("POST", "/v1/products/{product_id}/deactivate"),
        ("POST", "/v1/products/{product_id}/offers"),
        ("GET", "/v1/stores/{store_id}/offers"),
        ("PATCH", "/v1/offers/{offer_id}"),
        ("POST", "/v1/offers/{offer_id}/deactivate"),
        ("POST", "/v1/offers/{offer_id}/relist"),
        ("POST", "/v1/offers/{offer_id}/stock-adjustments"),
    ]:
        assert (m, p) in paths, (m, p)


def test_service_constructor_requires_all_args():
    with pytest.raises(TypeError):
        CatalogApplicationService()  # type: ignore[call-arg]
