"""구현체 연결(조립) 지점. 추상 ↔ 구현체 매핑은 이 파일에서만 한다 (R9)."""

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from auth.application.service import AuthApplicationService
from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.service import PasswordHasher, TokenProvider
from auth.infrastructure.repositories import (
    SqlAlchemyPointLogRepository,
    SqlAlchemyTokenBlacklistRepository,
    SqlAlchemyUserRepository,
)
from auth.infrastructure.security import BcryptPasswordHasher, JwtTokenProvider
from auth.presentation.dependencies import provide_auth_service
from database import get_db
from stores.application.service import StoresApplicationService
from stores.domain.repository import StoreRepository
from stores.domain.service import Clock as StoresClock
from stores.infrastructure.clock import SystemClock
from stores.infrastructure.repositories import SqlAlchemyStoreRepository
from stores.presentation.dependencies import provide_store_repository, provide_stores_service

# 상태 없는 유틸은 싱글턴 (세션을 가진 객체는 요청마다 만든다)
_password_hasher: PasswordHasher = BcryptPasswordHasher()
_token_provider: TokenProvider = JwtTokenProvider()
_stores_clock: StoresClock = SystemClock()


# ── auth ─────────────────────────────
def create_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def create_point_log_repository(session: AsyncSession = Depends(get_db)) -> PointLogRepository:
    return SqlAlchemyPointLogRepository(session)


def create_token_blacklist_repository(
    session: AsyncSession = Depends(get_db),
) -> TokenBlacklistRepository:
    return SqlAlchemyTokenBlacklistRepository(session)


def create_auth_service(
    session: AsyncSession = Depends(get_db),
    users: UserRepository = Depends(create_user_repository),
    point_logs: PointLogRepository = Depends(create_point_log_repository),
    blacklist: TokenBlacklistRepository = Depends(create_token_blacklist_repository),
) -> AuthApplicationService:
    return AuthApplicationService(
        session=session,
        users=users,
        point_logs=point_logs,
        blacklist=blacklist,
        hasher=_password_hasher,
        tokens=_token_provider,
    )


# ── stores ───────────────────────────
def create_store_repository(session: AsyncSession = Depends(get_db)) -> StoreRepository:
    return SqlAlchemyStoreRepository(session)


def create_stores_service(
    session: AsyncSession = Depends(get_db),
    stores: StoreRepository = Depends(create_store_repository),
) -> StoresApplicationService:
    return StoresApplicationService(session=session, stores=stores, clock=_stores_clock)


def wire_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_auth_service: create_auth_service,
            provide_store_repository: create_store_repository,
            provide_stores_service: create_stores_service,
        }
    )
