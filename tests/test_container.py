import inspect

import pytest
from fastapi import FastAPI

from auth.application.service import AuthApplicationService
from auth.domain.service import Clock as AuthClock
from auth.domain.service import PasswordHasher, TokenProvider
from auth.presentation import dependencies as auth_dependencies
from auth.presentation.dependencies import provide_auth_service
from container import (
    build_auth_service,
    build_reset_notifier,
    create_account_withdrawal_service,
    create_auth_service,
    create_password_reset_service,
    wire_dependencies,
)
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


def test_new_auth_provides_are_declared_and_wired():
    names = {fn.__name__ for fn in _provide_functions()}
    assert {"provide_password_reset_service", "provide_withdrawal_service"} <= names
    app = FastAPI()
    wire_dependencies(app)
    from auth.presentation.dependencies import provide_password_reset_service, provide_withdrawal_service

    assert app.dependency_overrides[provide_password_reset_service] is create_password_reset_service
    assert app.dependency_overrides[provide_withdrawal_service] is create_account_withdrawal_service


def test_withdrawal_and_reset_factories_build_with_abstractions():
    from auth.application.password_reset_service import PasswordResetService
    from auth.application.withdrawal_service import AccountWithdrawalService
    from auth.domain.service import PasswordResetNotifier, ResetCodeGenerator

    marker = object()
    reset = create_password_reset_service(marker, marker, marker)
    assert isinstance(reset, PasswordResetService)
    assert isinstance(reset.hasher, PasswordHasher)
    assert isinstance(reset.generator, ResetCodeGenerator)
    assert isinstance(reset.notifier, PasswordResetNotifier)
    service = create_account_withdrawal_service(marker, marker, marker, marker, marker)
    assert isinstance(service, AccountWithdrawalService)
    assert isinstance(service.clock, AuthClock)


def test_withdrawal_service_dependency_graph_has_no_cycle():
    """AccountWithdrawalService -> {auth, stores, catalog, reservations} 그래프가 순환 없이 풀린다 (R12)."""
    from fastapi.dependencies.utils import get_dependant

    dependant = get_dependant(path="/", call=create_account_withdrawal_service)
    assert len(dependant.dependencies) == 5


def test_auth_package_does_not_import_other_business_modules():
    """R12·R11: auth는 reservations·payments·stores·catalog·admin을 import하지 않는다."""
    import ast
    from pathlib import Path

    forbidden = {"reservations", "payments", "stores", "catalog", "admin", "container"}
    root = Path(__file__).resolve().parents[1] / "src" / "auth"
    offenders = []
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            offenders += [f"{path.name}: {m}" for m in modules if m.split(".")[0] in forbidden]
    assert offenders == []


def test_build_reset_notifier_selects_by_settings():
    from auth.infrastructure.reset_notifier import (
        LoggingPasswordResetNotifier,
        SmtpPasswordResetNotifier,
    )
    from auth.infrastructure.settings import MailSettings

    assert isinstance(build_reset_notifier(None), LoggingPasswordResetNotifier)
    settings = MailSettings(host="h", port=587, user="u", password="p", mail_from="a@b.com")
    assert isinstance(build_reset_notifier(settings), SmtpPasswordResetNotifier)  # 생성만, 발송 없음
