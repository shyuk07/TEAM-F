from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from auth.application.service import AuthApplicationService
from auth.domain.user import User
from auth.presentation.dependencies import bearer_scheme, provide_auth_service
from catalog.application.ports import (
    ReservationCancelPort,
    ReservationLookupPort,
    StorePort,
)
from catalog.application.service import CatalogApplicationService


def provide_catalog_service() -> CatalogApplicationService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("CatalogApplicationService 의존성이 주입되지 않았습니다.")


def provide_store_port() -> StorePort:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("StorePort 의존성이 주입되지 않았습니다.")


def provide_reservation_lookup() -> ReservationLookupPort:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("ReservationLookupPort 의존성이 주입되지 않았습니다.")


def provide_reservation_cancel() -> ReservationCancelPort:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("ReservationCancelPort 의존성이 주입되지 않았습니다.")


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthApplicationService, Depends(provide_auth_service)],
) -> User | None:
    if credentials is None or not credentials.credentials:
        return None  # 헤더 없음 = 비로그인
    return (await service.authenticate(credentials.credentials)).user  # 토큰 오류는 401


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
