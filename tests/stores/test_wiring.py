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
