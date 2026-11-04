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
from catalog.application.ports import (
    ReservationCancelPort,
    ReservationLookupPort,
    StorePort,
)
from catalog.application.service import CatalogApplicationService
from catalog.domain.repository.discount_offer_repository import DiscountOfferRepository
from catalog.domain.repository.product_repository import ProductRepository
from catalog.domain.repository.stock_log_repository import StockLogRepository
from catalog.domain.service import Clock as CatalogClock
from catalog.infrastructure.clock import SystemClock as CatalogSystemClock
from catalog.infrastructure.repositories import (
    SqlAlchemyDiscountOfferRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyStockLogRepository,
)
from catalog.infrastructure.reservation_cancel import NoReservationCancel
from catalog.infrastructure.reservation_lookup import NoReservationLookup
from catalog.presentation.dependencies import (
    provide_catalog_service,
    provide_reservation_cancel,
    provide_reservation_lookup,
    provide_store_port,
)
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
_catalog_clock: CatalogClock = CatalogSystemClock()
_reservation_lookup: ReservationLookupPort = NoReservationLookup()  # 임시 (CI-10)
_reservation_cancel: ReservationCancelPort = NoReservationCancel()  # 임시 (CI-11)


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


def build_auth_service(session: AsyncSession) -> AuthApplicationService:
    """Depends 없이 서비스를 만든다(lifespan 등 요청 밖). create_auth_service와 같은 구현체를 쓴다."""
    return create_auth_service(
        session,
        SqlAlchemyUserRepository(session),
        SqlAlchemyPointLogRepository(session),
        SqlAlchemyTokenBlacklistRepository(session),
    )


# ── stores ───────────────────────────
def create_store_repository(session: AsyncSession = Depends(get_db)) -> StoreRepository:
    return SqlAlchemyStoreRepository(session)


def create_stores_service(
    session: AsyncSession = Depends(get_db),
    stores: StoreRepository = Depends(create_store_repository),
) -> StoresApplicationService:
    return StoresApplicationService(session=session, stores=stores, clock=_stores_clock)


# ── catalog ──────────────────────────
def create_product_repository(session: AsyncSession = Depends(get_db)) -> ProductRepository:
    return SqlAlchemyProductRepository(session)


def create_discount_offer_repository(
    session: AsyncSession = Depends(get_db),
) -> DiscountOfferRepository:
    return SqlAlchemyDiscountOfferRepository(session)


def create_stock_log_repository(session: AsyncSession = Depends(get_db)) -> StockLogRepository:
    return SqlAlchemyStockLogRepository(session)


def create_store_port(
    stores_service: StoresApplicationService = Depends(create_stores_service),
) -> StorePort:
    return stores_service


def create_reservation_lookup() -> ReservationLookupPort:
    return _reservation_lookup


def create_reservation_cancel() -> ReservationCancelPort:
    return _reservation_cancel


def create_catalog_service(
    session: AsyncSession = Depends(get_db),
    stores: StorePort = Depends(create_store_port),
    products: ProductRepository = Depends(create_product_repository),
    offers: DiscountOfferRepository = Depends(create_discount_offer_repository),
    stock_logs: StockLogRepository = Depends(create_stock_log_repository),
    reservations: ReservationLookupPort = Depends(create_reservation_lookup),
    reservation_cancel: ReservationCancelPort = Depends(create_reservation_cancel),
) -> CatalogApplicationService:
    return CatalogApplicationService(
        session=session,
        stores=stores,
        products=products,
        offers=offers,
        stock_logs=stock_logs,
        clock=_catalog_clock,
        reservations=reservations,
        reservation_cancel=reservation_cancel,
    )


def wire_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_auth_service: create_auth_service,
            provide_store_repository: create_store_repository,
            provide_stores_service: create_stores_service,
            provide_store_port: create_store_port,
            provide_catalog_service: create_catalog_service,
            provide_reservation_lookup: create_reservation_lookup,
            provide_reservation_cancel: create_reservation_cancel,
        }
    )
