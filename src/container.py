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
from catalog.presentation.dependencies import (
    provide_catalog_service,
    provide_reservation_cancel,
    provide_reservation_lookup,
    provide_store_port,
)
from database import get_db
from reservations.application.adapters import PaymentRefundAdapter, PaymentReservationAdapter
from reservations.application.catalog_adapters import OfferReservationCanceller, OfferReservationLookup
from reservations.application.catalog_stock_adapter import CatalogStockAdapter
from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.ports import RefundPort, StockPort
from reservations.application.service import ReservationApplicationService
from reservations.domain.repository import ReservationRepository
from reservations.domain.service import Clock as ReservationsClock
from reservations.domain.service import PickupCodeGenerator
from reservations.infrastructure.clock import SystemClock as ReservationsSystemClock
from reservations.infrastructure.pickup_code import SecretsPickupCodeGenerator
from reservations.infrastructure.repositories import SqlAlchemyReservationRepository
from reservations.presentation.dependencies import (
    provide_reservation_lifecycle_service,
    provide_reservation_service,
)
from payments.application.ports import ReservationPort
from payments.application.service import PaymentApplicationService
from payments.domain.repository.payment_repository import PaymentRepository
from payments.domain.repository.refund_repository import RefundRepository
from payments.domain.service import Clock as PaymentsClock
from payments.domain.service import PaymentGateway
from payments.infrastructure.clock import SystemClock as PaymentsSystemClock
from payments.infrastructure.mock_gateway import MockPaymentGateway
from payments.infrastructure.repositories import (
    SqlAlchemyPaymentRepository,
    SqlAlchemyRefundRepository,
)
from payments.presentation.dependencies import provide_payment_service
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
_reservations_clock: ReservationsClock = ReservationsSystemClock()
_pickup_code_generator: PickupCodeGenerator = SecretsPickupCodeGenerator()
_payments_gateway: PaymentGateway = MockPaymentGateway()
_payments_clock: PaymentsClock = PaymentsSystemClock()


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
    """자리 표시 함수. 예약 구역이 아래에 있어 여기서 직접 만들 수 없다.
    wire_dependencies가 create_catalog_reservation_lookup(아래 예약 구역)으로 override한다."""
    raise NotImplementedError("wire_dependencies에서 create_catalog_reservation_lookup으로 교체됩니다.")


def create_reservation_cancel() -> ReservationCancelPort:
    """자리 표시 함수. wire_dependencies가 create_catalog_reservation_canceller(아래 예약 구역)로 override한다."""
    raise NotImplementedError("wire_dependencies에서 create_catalog_reservation_canceller로 교체됩니다.")


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


# ── reservations ─────────────────────
def create_reservation_repository(session: AsyncSession = Depends(get_db)) -> ReservationRepository:
    return SqlAlchemyReservationRepository(session)


def create_stock_port(
    offers: DiscountOfferRepository = Depends(create_discount_offer_repository),
    products: ProductRepository = Depends(create_product_repository),
    stores: StorePort = Depends(create_store_port),
    stock_logs: StockLogRepository = Depends(create_stock_log_repository),
) -> StockPort:
    # catalog 도메인·레포지토리만 쓰는 실제 재고 어댑터 (catalog 서비스는 받지 않는다: R12)
    return CatalogStockAdapter(offers=offers, products=products, stores=stores, stock_logs=stock_logs)


def create_refund_port() -> RefundPort:
    """자리 표시 함수. 결제 구역이 아래에 있어 여기서 직접 만들 수 없다.
    wire_dependencies가 create_reservation_refund_port(아래 결제 구역)로 override한다."""
    raise NotImplementedError("wire_dependencies에서 create_reservation_refund_port로 교체됩니다.")


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


def create_catalog_reservation_lookup(
    reservations: ReservationRepository = Depends(create_reservation_repository),
) -> ReservationLookupPort:
    """catalog용 예약 조회 포트. 위쪽 catalog 구역의 create_reservation_lookup을 옮기지 않고 override한다."""
    return OfferReservationLookup(reservations)


def create_catalog_reservation_canceller(
    service: ReservationApplicationService = Depends(create_reservation_service),
) -> ReservationCancelPort:
    """catalog용 일괄 취소 포트. 같은 요청 세션의 예약 서비스를 쓴다(R13). 예약 쪽은 catalog 서비스를 받지 않는다(R12)."""
    return OfferReservationCanceller(service)


# ── payments ─────────────────────────
def create_payment_repository(session: AsyncSession = Depends(get_db)) -> PaymentRepository:
    return SqlAlchemyPaymentRepository(session)


def create_refund_repository(session: AsyncSession = Depends(get_db)) -> RefundRepository:
    return SqlAlchemyRefundRepository(session)


def create_payment_reservation_port(
    lifecycle: ReservationLifecycleService = Depends(create_reservation_lifecycle_service),
) -> ReservationPort:
    return PaymentReservationAdapter(lifecycle)  # 같은 요청 세션의 lifecycle (R13)


def create_payment_service(
    session: AsyncSession = Depends(get_db),
    reservations: ReservationPort = Depends(create_payment_reservation_port),
    payments: PaymentRepository = Depends(create_payment_repository),
    refunds: RefundRepository = Depends(create_refund_repository),
) -> PaymentApplicationService:
    return PaymentApplicationService(
        session=session,
        reservations=reservations,
        payments=payments,
        refunds=refunds,
        gateway=_payments_gateway,
        clock=_payments_clock,
    )


def create_reservation_refund_port(
    payments: PaymentApplicationService = Depends(create_payment_service),
) -> RefundPort:
    """예약용 RefundPort. 위쪽 예약 구역의 create_refund_port를 옮기지 않고, wire_dependencies에서 이 함수로 override한다."""
    return PaymentRefundAdapter(payments)


def wire_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_auth_service: create_auth_service,
            provide_store_repository: create_store_repository,
            provide_stores_service: create_stores_service,
            provide_store_port: create_store_port,
            provide_catalog_service: create_catalog_service,
            provide_reservation_lookup: create_catalog_reservation_lookup,
            provide_reservation_cancel: create_catalog_reservation_canceller,
            provide_reservation_service: create_reservation_service,
            provide_reservation_lifecycle_service: create_reservation_lifecycle_service,
            provide_payment_service: create_payment_service,
            # 중첩 Depends도 override가 적용된다: create_reservation_service가 받는 RefundPort를 결제 어댑터로 교체
            create_refund_port: create_reservation_refund_port,
            # catalog 서비스가 받는 포트도 같은 방식으로 교체 (정의 순서 때문에 위쪽 함수를 옮기지 않는다)
            create_reservation_lookup: create_catalog_reservation_lookup,
            create_reservation_cancel: create_catalog_reservation_canceller,
        }
    )
