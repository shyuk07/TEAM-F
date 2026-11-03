"""구현체 연결(조립) 지점. 추상 ↔ 구현체 매핑은 이 파일에서만 한다 (R9)."""

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from stores.application.service import StoresApplicationService
from stores.domain.repository import StoreRepository
from stores.infrastructure.clock import SystemClock
from stores.infrastructure.repositories import SqlAlchemyStoreRepository
from stores.presentation.dependencies import provide_store_repository, provide_stores_service

# ── stores ───────────────────────────
_clock = SystemClock()  # 상태 없는 유틸은 싱글턴


def create_store_repository(session: AsyncSession = Depends(get_db)) -> StoreRepository:
    return SqlAlchemyStoreRepository(session)


def create_stores_service(
    session: AsyncSession = Depends(get_db),
    stores: StoreRepository = Depends(create_store_repository),
) -> StoresApplicationService:
    return StoresApplicationService(session=session, stores=stores, clock=_clock)


def wire_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_store_repository: create_store_repository,
            provide_stores_service: create_stores_service,
        }
    )
