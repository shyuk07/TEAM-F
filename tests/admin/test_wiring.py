"""조립 테스트: provide_* 매핑(R9), 포트 구조적 일치(R10), 미연계 자리표시자 단언 (admin.md 7, 9절)."""

import inspect

import pytest
from fastapi import FastAPI

from admin.application import ports
from admin.application.service import AdminApplicationService
from admin.infrastructure.reservation_admin import NoReservationAdmin
from admin.presentation import dependencies as deps
from auth.application.service import AuthApplicationService
from catalog.application.service import CatalogApplicationService
from container import create_admin_service, create_reservation_admin, wire_dependencies
from main import app
from stores.application.service import StoresApplicationService

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _provides():
    return [
        fn
        for name, fn in inspect.getmembers(deps, inspect.isfunction)
        if name.startswith("provide_") and fn.__module__ == deps.__name__
    ]


def test_provide_admin_service_is_wired():
    assert [f.__name__ for f in _provides()] == ["provide_admin_service"]
    fresh = FastAPI()
    wire_dependencies(fresh)
    assert fresh.dependency_overrides[deps.provide_admin_service] is create_admin_service
    assert app.dependency_overrides[deps.provide_admin_service] is create_admin_service


def test_placeholder_raises_when_not_wired():
    with pytest.raises(NotImplementedError):
        deps.provide_admin_service()


def test_reservation_admin_is_still_the_placeholder():
    # 임시 구현(미연계, R16). reservations가 연결되면 이 단언이 실패해 바인딩 교체를 상기시킨다 (admin.md C10).
    assert isinstance(create_reservation_admin(), NoReservationAdmin)


async def test_no_reservation_admin_does_nothing():
    import uuid

    placeholder = NoReservationAdmin()
    assert await placeholder.cancel_reserved_for_user(uuid.uuid4(), reason="x") == 0
    assert await placeholder.has_reserved_for_store(uuid.uuid4()) is False


def _shape(fn):
    sig = inspect.signature(fn)
    return [(n, p.kind, p.default) for n, p in sig.parameters.items() if n != "self"]


@pytest.mark.parametrize(
    "port, service",
    [
        (ports.AccountAdminPort, AuthApplicationService),
        (ports.StoreAdminPort, StoresApplicationService),
        (ports.OfferAdminPort, CatalogApplicationService),
    ],
)
def test_real_services_satisfy_port_signatures(port, service):
    names = [
        n for n, v in vars(port).items() if inspect.iscoroutinefunction(v) and not n.startswith("_")
    ]
    assert names
    for name in names:
        real = getattr(service, name)
        assert inspect.iscoroutinefunction(real), name
        assert _shape(real) == _shape(getattr(port, name)), name


def test_admin_service_constructor_requires_all_args():
    with pytest.raises(TypeError):
        AdminApplicationService()  # type: ignore[call-arg]


def test_admin_routes_registered_without_colliding_with_auth_admin_routes():
    paths = {
        (method.upper(), path) for path, item in app.openapi()["paths"].items() for method in item
    }
    for m, p in [
        ("PATCH", "/v1/admin/owners/{owner_id}/approve"),
        ("PATCH", "/v1/admin/owners/{owner_id}/reject"),
        ("PATCH", "/v1/admin/users/{user_id}/suspend"),
        ("DELETE", "/v1/admin/users/{user_id}"),
        ("PATCH", "/v1/admin/stores/{store_id}/suspend"),
        ("PATCH", "/v1/admin/stores/{store_id}/close"),
        ("PATCH", "/v1/admin/offers/{offer_id}/suspend"),
        ("GET", "/v1/admin/users/{user_id}/points"),
        ("POST", "/v1/admin/users/{user_id}/points"),
        # auth 관리자 EP(GET /v1/admin/users/{user_id}, POST /v1/admin/token-blacklist/purge)는
        # main 7594d43에서 auth에서 제거됨. admin 모듈로 옮기는 작업은 후속 PR.
    ]:
        assert (m, p) in paths, (m, p)
