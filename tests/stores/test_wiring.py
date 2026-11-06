import inspect

import pytest

from container import create_store_repository, create_stores_service, wire_dependencies
from main import app
from stores.presentation import dependencies as deps


def test_all_provides_are_wired():
    provides = [
        fn
        for name, fn in inspect.getmembers(deps, inspect.isfunction)
        if name.startswith("provide_")
    ]
    assert provides
    for fn in provides:
        assert fn in app.dependency_overrides, fn.__name__
    assert app.dependency_overrides[deps.provide_store_repository] is create_store_repository
    assert app.dependency_overrides[deps.provide_stores_service] is create_stores_service


def test_wire_dependencies_idempotent():
    wire_dependencies(app)
    assert deps.provide_stores_service in app.dependency_overrides


def test_store_port_is_query_service_and_graph_is_acyclic():
    import container
    from stores.application.query_service import StoreQueryService
    from stores.application.service import StoresApplicationService
    from stores.domain.repository import StoreRepository

    class Repo(StoreRepository):
        async def find_by_id(self, store_id, for_update=False): ...
        async def find_by_ids(self, store_ids): ...
        async def find_by_owner_id(self, owner_id, for_update=False): ...
        async def exists_by_name_and_address(self, name, pickup_address): ...
        async def find_visible_near(self, *, latitude, longitude, radius_km): ...
        async def save(self, store): ...

    repo = Repo()
    query = container.create_store_query_service(repo)
    assert isinstance(query, StoreQueryService)
    assert container.create_store_port(query) is query
    assert app.dependency_overrides[deps.provide_stores_service] is container.create_stores_service
    with pytest.raises(NotImplementedError):  # 자리 표시 함수. 실제 객체는 wire_dependencies가 바꾼다 (D-36)
        container.create_pickup_pending_port()
    assert (
        app.dependency_overrides[container.create_pickup_pending_port]
        is container.create_store_reservation_query
    )
    port = container.create_store_reservation_query(object(), object())
    geocoder = container.create_geocoder()
    service = container.create_stores_service(None, repo, object(), port, geocoder)
    assert isinstance(service, StoresApplicationService)
    assert service.pickup_pending is port and service.geocoder is geocoder


def test_dependency_graph_resolves_without_cycle():
    from fastapi.dependencies.utils import get_dependant

    import container

    def walk(dependant, seen):
        for sub in dependant.dependencies:
            assert sub.call not in seen, "순환 의존"
            walk(sub, seen | {sub.call})

    for fn in (container.create_stores_service, container.create_catalog_service,
               container.create_admin_service, container.create_store_port):
        walk(get_dependant(path="/", call=fn), {fn})


def test_create_geocoder_returns_naver_geocoder_singleton():
    import container
    from stores.domain.service import Geocoder
    from stores.infrastructure.geocoder import NaverGeocoder

    geocoder = container.create_geocoder()
    assert isinstance(geocoder, Geocoder) and isinstance(geocoder, NaverGeocoder)
    assert container.create_geocoder() is geocoder


def test_import_main_succeeds_without_naver_keys():
    """키가 없어도 서버가 시작된다 (stores.md D28). 빈 값으로 덮어써 .env의 실제 키도 무시한다."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    env = dict(os.environ)
    env.update(
        NAVER_MAP_CLIENT_ID="",
        NAVER_MAP_CLIENT_SECRET="",
        DATABASE_URL="postgresql+asyncpg://x:x@localhost/x",
        JWT_SECRET_KEY="test-secret-key-for-pytest-0123456789abcdef",
        PYTHONIOENCODING="utf-8",
    )
    src = Path(__file__).resolve().parents[2] / "src"
    done = subprocess.run(
        [sys.executable, "-c", "import main; print('IMPORT_OK')"],
        cwd=src, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert done.returncode == 0 and "IMPORT_OK" in done.stdout, done.stderr
