from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.application.password_reset_service import PasswordResetService
from auth.application.service import AuthApplicationService, AuthenticatedPrincipal
from auth.application.withdrawal_service import AccountWithdrawalService
from auth.domain.exceptions import AuthenticationError
from auth.domain.user import Role, User

bearer_scheme = HTTPBearer(auto_error=False)


def provide_auth_service() -> AuthApplicationService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("AuthApplicationService 의존성이 주입되지 않았습니다.")


def provide_password_reset_service() -> PasswordResetService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("PasswordResetService 의존성이 주입되지 않았습니다.")


def provide_withdrawal_service() -> AccountWithdrawalService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("AccountWithdrawalService 의존성이 주입되지 않았습니다.")


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthApplicationService, Depends(provide_auth_service)],
) -> AuthenticatedPrincipal:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("로그인이 필요합니다.")
    return await service.authenticate(credentials.credentials)


async def get_current_user(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal)],
) -> User:
    return principal.user


async def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthApplicationService, Depends(provide_auth_service)],
) -> User | None:
    """로그인 선택: 인증 정보가 없으면 None, 있는데 유효하지 않으면 401."""
    if credentials is not None and credentials.credentials:
        return (await service.authenticate(credentials.credentials)).user
    raw = request.headers.get("authorization")
    if raw is None or not raw.strip():
        return None
    # HTTPBearer는 헤더 없음과 Bearer가 아닌 헤더를 구분하지 못하므로 raw 헤더로 가른다.
    raise AuthenticationError("로그인이 필요합니다.")


async def get_current_principal_allow_suspended(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthApplicationService, Depends(provide_auth_service)],
) -> AuthenticatedPrincipal:
    """정지된 계정도 통과한다. 탈퇴·폐기·위조 토큰은 그대로 401 (D35)."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("로그인이 필요합니다.")
    return await service.authenticate(credentials.credentials, allow_suspended=True)


async def get_current_user_allow_suspended(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_principal_allow_suspended)],
) -> User:
    return principal.user


def require_roles(*roles: Role):
    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        user.require_role(*roles)
        return user

    return checker


def require_roles_allow_suspended(*roles: Role):
    async def checker(user: Annotated[User, Depends(get_current_user_allow_suspended)]) -> User:
        user.require_role(*roles)
        return user

    return checker


def require_approved_owner():
    """상점 개설·폐점용. 역할 403이 먼저, 그다음 승인 여부 403 (D5)."""

    async def checker(user: Annotated[User, Depends(require_roles(Role.OWNER))]) -> User:
        user.ensure_approved_owner()
        return user

    return checker


CurrentPrincipal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]
PrincipalAllowSuspended = Annotated[
    AuthenticatedPrincipal, Depends(get_current_principal_allow_suspended)
]
CurrentUser = Annotated[User, Depends(get_current_user)]
CustomerUser = Annotated[User, Depends(require_roles(Role.CUSTOMER))]
OwnerUser = Annotated[User, Depends(require_roles(Role.OWNER))]
AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
ApprovedOwnerUser = Annotated[User, Depends(require_approved_owner())]
# 픽업 EP 전용: 정지된 상점주도 통과한다 (D35). reservations 픽업 EP(`reservations/presentation/router.py`)가 사용한다.
SuspendedAllowedOwnerUser = Annotated[
    User, Depends(require_roles_allow_suspended(Role.OWNER))
]
