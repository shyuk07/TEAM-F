import inspect

import pytest
from fastapi import FastAPI

from auth.application.service import AuthApplicationService
from auth.domain.service import Clock as AuthClock
from auth.domain.service import PasswordHasher, TokenProvider
from auth.presentation import dependencies as auth_dependencies
from auth.presentation.dependencies import provide_auth_service
from container import build_auth_service, create_auth_service, wire_dependencies
from stores.presentation import dependencies as stores_dependencies

# 새 모듈이 생기면 그 모듈의 dependencies를 추가한다.
DEPENDENCY_MODULES = [auth_dependencies, stores_dependencies]


def _provide_functions():
    return [
        fn
        for mod in DEPENDENCY_MODULES
        for name, fn in inspect.getmembers(mod, inspect.isfunction)
        if name.startswith("provide_") and fn.__module__ == mod.__name__
    ]


def test_every_provide_function_is_wired():
    app = FastAPI()
    wire_dependencies(app)
    provides = _provide_functions()
    assert provides
    for fn in provides:
        assert fn in app.dependency_overrides, f"{fn.__name__}이 wire_dependencies에 없습니다."


def test_placeholder_raises_when_not_wired():
    with pytest.raises(NotImplementedError):
        provide_auth_service()


def test_create_auth_service_builds_with_abstractions():
    marker = object()
    service = create_auth_service(marker, marker, marker, marker)
    assert isinstance(service, AuthApplicationService)
    assert service.session is marker
    assert isinstance(service.hasher, PasswordHasher)
    assert isinstance(service.tokens, TokenProvider)
    assert isinstance(service.clock, AuthClock)


def test_build_auth_service_builds_with_abstractions():
    marker = object()
    service = build_auth_service(marker)
    assert isinstance(service, AuthApplicationService)
    assert service.session is marker
    assert isinstance(service.hasher, PasswordHasher)
    assert isinstance(service.tokens, TokenProvider)
