"""구현체 연결(조립) 지점. 추상 ↔ 구현체 매핑은 이 파일에서만 한다 (R9)."""

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from admin.application.ports import ReservationAdminPort
from admin.application.service import AdminApplicationService
from admin.domain.service import Clock as AdminClock
from admin.infrastructure.clock import SystemClock as AdminSystemClock
from admin.infrastructure.reservation_admin import NoReservationAdmin
from admin.presentation.dependencies import provide_admin_service
from auth.application.service import AuthApplicationService
from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.service import Clock as AuthClock
from auth.domain.service import PasswordHasher, TokenProvider
from auth.infrastructure.clock import SystemClock as AuthSystemClock
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
from reservations.application.interim_stock_port import ReadOnlyOfferStockPort
from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.ports import RefundPort, StockPort
from reservations.application.service import ReservationApplicationService
from reservations.domain.repository import ReservationRepository
from reservations.domain.service import Clock as ReservationsClock
from reservations.domain.service import PickupCodeGenerator
from reservations.infrastructure.clock import SystemClock as ReservationsSystemClock
from reservations.infrastructure.payment_refund_stub import NoPaymentRefund
from reservations.infrastructure.pickup_code import SecretsPickupCodeGenerator
from reservations.infrastructure.repositories import SqlAlchemyReservationRepository
from reservations.presentation.dependencies import (
    provide_reservation_lifecycle_service,
    provide_reservation_service,
)
from stores.application.ports import OpenOffersPort, PickupPendingPort
from stores.application.query_service import StoreQueryService
from stores.application.service import StoresApplicationService
from stores.domain.repository import StoreRepository
from stores.domain.service import Clock as StoresClock
from stores.domain.service import Geocoder
from stores.infrastructure.clock import SystemClock
from stores.infrastructure.geocoder import NaverGeocoder
from stores.infrastructure.pickup_pending import NoPickupPendingReservations
from stores.infrastructure.repositories import SqlAlchemyStoreRepository
from stores.infrastructure.settings import get_naver_geocoding_settings
from stores.presentation.dependencies import provide_store_repository, provide_stores_service

# 상태 없는 유틸은 싱글턴 (세션을 가진 객체는 요청마다 만든다)
_password_hasher: PasswordHasher = BcryptPasswordHasher()
_token_provider: TokenProvider = JwtTokenProvider()
_auth_clock: AuthClock = AuthSystemClock()
_stores_clock: StoresClock = SystemClock()
_catalog_clock: CatalogClock = CatalogSystemClock()
_reservation_lookup: ReservationLookupPort = NoReservationLookup()  # 임시 (CI-10)
_reservation_cancel: ReservationCancelPort = NoReservationCancel()  # 임시 (CI-11)
_reservations_clock: ReservationsClock = ReservationsSystemClock()
_pickup_code_generator: PickupCodeGenerator = SecretsPickupCodeGenerator()
_payment_refund: RefundPort = NoPaymentRefund()  # 임시 (D-15, C-4)
_pickup_pending: PickupPendingPort = NoPickupPendingReservations()  # 임시 미연계 (stores.md D21): reservations 후속 PR이 교체
# 네이버 지오코딩: NAVER_MAP_* 환경변수가 없으면 개설이 503 (stores.md D28)
_geocoder: Geocoder = NaverGeocoder(get_naver_geocoding_settings())
_admin_clock: AdminClock = AdminSystemClock()
_reservation_admin: ReservationAdminPort = NoReservationAdmin()  # 임시 (admin.md B-6, C10): reservations 후속 PR이 교체


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
        clock=_auth_clock,
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


def create_store_query_service(
    stores: StoreRepository = Depends(create_store_repository),
) -> StoreQueryService:
    return StoreQueryService(stores=stores)


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
    query: StoreQueryService = Depends(create_store_query_service),
) -> StorePort:
    return query


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


# ── stores (쓰기: catalog 뒤에 정의, R12) ──
def create_open_offers_port(
    catalog: CatalogApplicationService = Depends(create_catalog_service),
) -> OpenOffersPort:
    return catalog


def create_pickup_pending_port() -> PickupPendingPort:
    return _pickup_pending


def create_geocoder() -> Geocoder:
    return _geocoder


def create_stores_service(
    session: AsyncSession = Depends(get_db),
    stores: StoreRepository = Depends(create_store_repository),
    open_offers: OpenOffersPort = Depends(create_open_offers_port),
    pickup_pending: PickupPendingPort = Depends(create_pickup_pending_port),
    geocoder: Geocoder = Depends(create_geocoder),
) -> StoresApplicationService:
    return StoresApplicationService(
        session=session,
        stores=stores,
        clock=_stores_clock,
        open_offers=open_offers,
        pickup_pending=pickup_pending,
        geocoder=geocoder,
    )


# ── reservations ─────────────────────
def create_reservation_repository(session: AsyncSession = Depends(get_db)) -> ReservationRepository:
    return SqlAlchemyReservationRepository(session)


def create_stock_port(
    offers: DiscountOfferRepository = Depends(create_discount_offer_repository),
    products: ProductRepository = Depends(create_product_repository),
    stores: StorePort = Depends(create_store_port),
) -> StockPort:
    # 임시 읽기 전용 구현 (D-25). catalog의 재고 서비스(C-1)가 생기면 교체한다.
    return ReadOnlyOfferStockPort(offers=offers, products=products, stores=stores)


def create_refund_port() -> RefundPort:
    return _payment_refund


def create_reservation_lifecycle_service(
    session: AsyncSession = Depends(get_db),
    reservations: ReservationRepository = Depends(create_reservation_repository),
    stock: StockPort = Depends(create_stock_port),
) -> ReservationLifecycleService:
    return ReservationLifecycleService(
        session=session, reservations=reservations, stock=stock, clock=_reservations_clock
    )


def create_reservation_service(
    session: AsyncSession = Depends(get_db),
    lifecycle: ReservationLifecycleService = Depends(create_reservation_lifecycle_service),
    reservations: ReservationRepository = Depends(create_reservation_repository),
    stock: StockPort = Depends(create_stock_port),
    refunds: RefundPort = Depends(create_refund_port),
) -> ReservationApplicationService:
    return ReservationApplicationService(
        session=session,
        lifecycle=lifecycle,
        reservations=reservations,
        stock=stock,
        refunds=refunds,
        clock=_reservations_clock,
        code_generator=_pickup_code_generator,
    )


# ── admin ────────────────────────────
def create_reservation_admin() -> ReservationAdminPort:
    return _reservation_admin


def create_admin_service(
    session: AsyncSession = Depends(get_db),
    accounts: AuthApplicationService = Depends(create_auth_service),
    stores: StoresApplicationService = Depends(create_stores_service),
    offers: CatalogApplicationService = Depends(create_catalog_service),
    reservations: ReservationAdminPort = Depends(create_reservation_admin),
) -> AdminApplicationService:
    return AdminApplicationService(
        session=session,
        accounts=accounts,
        stores=stores,
        offers=offers,
        reservations=reservations,
        clock=_admin_clock,
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
            provide_reservation_service: create_reservation_service,
            provide_reservation_lifecycle_service: create_reservation_lifecycle_service,
            provide_admin_service: create_admin_service,
        }
    )
