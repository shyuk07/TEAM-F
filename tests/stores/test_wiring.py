import inspect

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
        async def save(self, store): ...

    repo = Repo()
    query = container.create_store_query_service(repo)
    assert isinstance(query, StoreQueryService)
    assert container.create_store_port(query) is query
    assert app.dependency_overrides[deps.provide_stores_service] is container.create_stores_service
    port = container.create_pickup_pending_port()
    service = container.create_stores_service(None, repo, object(), port)
    assert isinstance(service, StoresApplicationService)
    assert service.pickup_pending is port


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
