import inspect

import pytest
from fastapi import FastAPI

from catalog.application.service import CatalogApplicationService
from catalog.presentation import dependencies as deps
from container import (
    create_catalog_reservation_canceller,
    create_catalog_reservation_lookup,
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
    # 실제 예약 어댑터로 연결된다. 위쪽 catalog 구역의 자리 표시 함수(create_reservation_*)도 같은 팩토리로 override된다
    for overrides in (fresh.dependency_overrides, app.dependency_overrides):
        assert overrides[deps.provide_reservation_lookup] is create_catalog_reservation_lookup
        assert overrides[create_reservation_lookup] is create_catalog_reservation_lookup
        assert overrides[deps.provide_reservation_cancel] is create_catalog_reservation_canceller
        assert overrides[create_reservation_cancel] is create_catalog_reservation_canceller


def test_reservation_port_placeholders_are_not_silent_stubs():
    with pytest.raises(NotImplementedError):
        create_reservation_lookup()
    with pytest.raises(NotImplementedError):
        create_reservation_cancel()


@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_container_graph_connects_real_reservation_adapters_on_same_session(anyio_backend):
    """catalog 서비스가 실제 예약 어댑터를 받고, 예약 서비스와 같은 세션을 쓴다. NameError·순환 없음."""
    import httpx
    from fastapi import Depends

    from database import get_db
    from reservations.application.catalog_adapters import OfferReservationCanceller, OfferReservationLookup
    from reservations.application.catalog_stock_adapter import CatalogStockAdapter

    probe = FastAPI()
    wire_dependencies(probe)
    session = object()
    probe.dependency_overrides[get_db] = lambda: session
    seen = {}

    @probe.get("/probe")
    async def route(service: CatalogApplicationService = Depends(deps.provide_catalog_service)):
        seen["catalog"] = service
        return {}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=probe), base_url="http://t") as client:
        assert (await client.get("/probe")).status_code == 200

    catalog = seen["catalog"]
    assert isinstance(catalog.reservations, OfferReservationLookup)
    assert isinstance(catalog.reservation_cancel, OfferReservationCanceller)
    reservation_service = catalog.reservation_cancel.service
    assert catalog.session is session and reservation_service.session is session  # 같은 요청 세션 (R13)
    stock = reservation_service.stock
    assert isinstance(stock, CatalogStockAdapter)
    # R12: 예약·결제·재고 어댑터 경로에 catalog 서비스가 되돌아오지 않는다 (재고 어댑터는 catalog 레포만 쓴다)
    for owner in (stock, reservation_service.lifecycle, reservation_service.refunds, reservation_service.refunds.payments):
        assert not isinstance(owner, CatalogApplicationService)
    assert not any(isinstance(v, CatalogApplicationService) for v in vars(stock).values())


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
        ("GET", "/v1/products"),
        ("GET", "/v1/offers"),
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
