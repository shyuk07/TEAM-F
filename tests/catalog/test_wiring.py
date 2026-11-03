import inspect

import pytest
from fastapi import FastAPI

from catalog.application.service import CatalogApplicationService
from catalog.presentation import dependencies as deps
from container import create_catalog_service, create_store_port, wire_dependencies
from main import app


def _provides():
    return [
        fn
        for name, fn in inspect.getmembers(deps, inspect.isfunction)
        if name.startswith("provide_") and fn.__module__ == deps.__name__
    ]


def test_all_provides_are_wired():
    provides = _provides()
    assert {f.__name__ for f in provides} == {"provide_catalog_service", "provide_store_port"}
    fresh = FastAPI()
    wire_dependencies(fresh)
    for fn in provides:
        assert fn in fresh.dependency_overrides, fn.__name__
        assert fn in app.dependency_overrides, fn.__name__
    assert fresh.dependency_overrides[deps.provide_catalog_service] is create_catalog_service
    assert fresh.dependency_overrides[deps.provide_store_port] is create_store_port


def test_placeholders_raise_when_not_wired():
    with pytest.raises(NotImplementedError):
        deps.provide_catalog_service()
    with pytest.raises(NotImplementedError):
        deps.provide_store_port()


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
        ("POST", "/v1/offers/{offer_id}/relist"),
        ("POST", "/v1/offers/{offer_id}/stock-adjustments"),
    ]:
        assert (m, p) in paths, (m, p)


def test_service_constructor_requires_all_args():
    with pytest.raises(TypeError):
        CatalogApplicationService()  # type: ignore[call-arg]
