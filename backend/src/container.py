"""구현체 연결(조립) 지점. 추상 ↔ 구현체 매핑은 이 파일에서만 한다 (R9)."""

import logging

from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from admin.application.ports import ReservationAdminPort
from admin.application.service import AdminApplicationService
from admin.domain.service import Clock as AdminClock
from admin.infrastructure.clock import SystemClock as AdminSystemClock
from admin.presentation.dependencies import provide_admin_service
from auth.application.password_reset_service import PasswordResetService
from auth.application.service import AuthApplicationService
from auth.application.withdrawal_service import AccountWithdrawalService
from auth.domain.repository.password_reset_code_repository import PasswordResetCodeRepository
from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.service import Clock as AuthClock
from auth.domain.service import (
    EmailFingerprint,
    PasswordHasher,
    PasswordResetNotifier,
    ResetCodeGenerator,
    TokenProvider,
)
from auth.infrastructure.clock import SystemClock as AuthSystemClock
from auth.infrastructure.repositories import (
    SqlAlchemyPasswordResetCodeRepository,
    SqlAlchemyPointLogRepository,
    SqlAlchemyTokenBlacklistRepository,
    SqlAlchemyUserRepository,
)
from auth.infrastructure.reset_notifier import (
    LoggingPasswordResetNotifier,
    SmtpPasswordResetNotifier,
)
from auth.infrastructure.security import (
    BcryptPasswordHasher,
    HmacEmailFingerprint,
    JwtTokenProvider,
    SecretsResetCodeGenerator,
)
from auth.infrastructure.settings import MailSettings, get_mail_settings
from auth.presentation.dependencies import (
    provide_auth_service,
    provide_password_reset_service,
    provide_withdrawal_service,
)
from catalog.application.ports import (
    ReservationCancelPort,
    ReservationLookupPort,
    StorePort,
)
from catalog.application.service import CatalogApplicationService
from catalog.domain.repository.discount_offer_repository import DiscountOfferRepository
from catalog.domain.repository.product_image_repository import ProductImageRepository
from catalog.domain.repository.product_repository import ProductRepository
from catalog.domain.repository.stock_log_repository import StockLogRepository
from catalog.domain.service import Clock as CatalogClock
from catalog.infrastructure.clock import SystemClock as CatalogSystemClock
from catalog.infrastructure.repositories import (
    SqlAlchemyDiscountOfferRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyProductImageRepository,
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
from reservations.application.admin_adapters import AdminWithdrawalReservationAdapter, ReservationAdminAdapter
from reservations.application.catalog_adapters import OfferReservationCanceller, OfferReservationLookup
from reservations.application.catalog_stock_adapter import CatalogStockAdapter
from reservations.application.lifecycle_service import ReservationLifecycleService
from reservations.application.ports import RefundPort, StoreOffersPort, StockPort
from reservations.application.service import ReservationApplicationService
from reservations.application.store_adapters import CatalogStoreOffersAdapter
from reservations.application.store_query import StoreReservationQuery
from reservations.application.store_reservation_service import StoreReservationListService
from reservations.domain.repository import ReservationRepository
from reservations.domain.service import Clock as ReservationsClock
from reservations.domain.service import PickupCodeGenerator
from reservations.infrastructure.clock import SystemClock as ReservationsSystemClock
from reservations.infrastructure.pickup_code import SecretsPickupCodeGenerator
from reservations.infrastructure.repositories import SqlAlchemyReservationRepository
from reservations.presentation.dependencies import (
    provide_reservation_lifecycle_service,
    provide_reservation_service,
    provide_store_reservation_list_service,
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
from stores.application.ports import OpenOffersPort, PickupPendingPort
from stores.application.query_service import StoreQueryService
from stores.application.service import StoresApplicationService
from stores.domain.repository import StoreRepository
from stores.domain.service import Clock as StoresClock
from stores.domain.service import Geocoder
from stores.infrastructure.clock import SystemClock
from stores.infrastructure.geocoder import KakaoGeocoder
from stores.infrastructure.mock_geocoder import MockGeocoder
from stores.infrastructure.repositories import SqlAlchemyStoreRepository
from stores.infrastructure.settings import get_kakao_geocoding_settings
from stores.presentation.dependencies import (
    provide_store_query_service,
    provide_store_repository,
    provide_stores_service,
)

logger = logging.getLogger(__name__)


def build_reset_notifier(settings: MailSettings | None) -> PasswordResetNotifier:
    """SMTP 설정이 있으면 메일, 없으면 로그(개발용)로 재설정 코드를 전달한다. 설정 값은 로그에 남기지 않는다."""
    if settings is None:
        logger.warning("SMTP 설정이 없어 재설정 코드를 로그로 전달합니다(개발용)")
        return LoggingPasswordResetNotifier()
    logger.info("재설정 코드 전달: SMTP (host=%s)", settings.host)
    return SmtpPasswordResetNotifier(settings)


# 상태 없는 유틸은 싱글턴 (세션을 가진 객체는 요청마다 만든다)
_password_hasher: PasswordHasher = BcryptPasswordHasher()
_token_provider: TokenProvider = JwtTokenProvider()
_email_fingerprint: EmailFingerprint = HmacEmailFingerprint()
_auth_clock: AuthClock = AuthSystemClock()
_reset_code_generator: ResetCodeGenerator = SecretsResetCodeGenerator()
_reset_notifier: PasswordResetNotifier = build_reset_notifier(get_mail_settings())
_stores_clock: StoresClock = SystemClock()
_catalog_clock: CatalogClock = CatalogSystemClock()
_reservations_clock: ReservationsClock = ReservationsSystemClock()
_pickup_code_generator: PickupCodeGenerator = SecretsPickupCodeGenerator()
_payments_gateway: PaymentGateway = MockPaymentGateway()
_payments_clock: PaymentsClock = PaymentsSystemClock()
# 카카오 지오코딩: KAKAO_REST_API_KEY가 없으면 로컬 개발용 MockGeocoder로 폴백
_kakao_settings = get_kakao_geocoding_settings()
_geocoder: Geocoder = KakaoGeocoder(_kakao_settings) if _kakao_settings else MockGeocoder()
_admin_clock: AdminClock = AdminSystemClock()


# ── auth ─────────────────────────────
def create_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def create_point_log_repository(session: AsyncSession = Depends(get_db)) -> PointLogRepository:
    return SqlAlchemyPointLogRepository(session)


def create_token_blacklist_repository(
    session: AsyncSession = Depends(get_db),
) -> TokenBlacklistRepository:
    return SqlAlchemyTokenBlacklistRepository(session)


def create_password_reset_code_repository(
    session: AsyncSession = Depends(get_db),
) -> PasswordResetCodeRepository:
    return SqlAlchemyPasswordResetCodeRepository(session)


def create_auth_service(
    session: AsyncSession = Depends(get_db),
    users: UserRepository = Depends(create_user_repository),
    point_logs: PointLogRepository = Depends(create_point_log_repository),
    blacklist: TokenBlacklistRepository = Depends(create_token_blacklist_repository),
    codes: PasswordResetCodeRepository = Depends(create_password_reset_code_repository),
) -> AuthApplicationService:
    return AuthApplicationService(
        session=session,
        users=users,
        point_logs=point_logs,
        blacklist=blacklist,
        hasher=_password_hasher,
        tokens=_token_provider,
        clock=_auth_clock,
        codes=codes,
        email_fingerprint=_email_fingerprint,
    )


def create_password_reset_service(
    session: AsyncSession = Depends(get_db),
    users: UserRepository = Depends(create_user_repository),
    codes: PasswordResetCodeRepository = Depends(create_password_reset_code_repository),
) -> PasswordResetService:
    return PasswordResetService(
        session=session,
        users=users,
        codes=codes,
        hasher=_password_hasher,
        generator=_reset_code_generator,
        notifier=_reset_notifier,
        clock=_auth_clock,
    )


def build_auth_service(session: AsyncSession) -> AuthApplicationService:
    """Depends 없이 서비스를 만든다(lifespan 등 요청 밖). create_auth_service와 같은 구현체를 쓴다."""
    return create_auth_service(
        session,
        SqlAlchemyUserRepository(session),
        SqlAlchemyPointLogRepository(session),
        SqlAlchemyTokenBlacklistRepository(session),
        SqlAlchemyPasswordResetCodeRepository(session),
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


def create_product_image_repository(
    session: AsyncSession = Depends(get_db),
) -> ProductImageRepository:
    return SqlAlchemyProductImageRepository(session)


def create_store_port(
    query: StoreQueryService = Depends(create_store_query_service),
) -> StorePort:
    return query


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
    product_images: ProductImageRepository = Depends(create_product_image_repository),
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
        product_images=product_images,
    )


# ── stores (쓰기: catalog 뒤에 정의, R12) ──
def create_open_offers_port(
    catalog: CatalogApplicationService = Depends(create_catalog_service),
) -> OpenOffersPort:
    return catalog


def create_pickup_pending_port() -> PickupPendingPort:
    """자리 표시 함수. 예약 구역이 아래에 있어 여기서 직접 만들 수 없다.
    wire_dependencies가 create_store_reservation_query(아래 예약 구역)로 override한다."""
    raise NotImplementedError("wire_dependencies에서 create_store_reservation_query로 교체됩니다.")


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


def create_store_offers_port(
    offers: DiscountOfferRepository = Depends(create_discount_offer_repository),
) -> StoreOffersPort:
    return CatalogStoreOffersAdapter(offers)  # catalog 추상 레포지토리만 사용 (R11, R12)


def create_store_reservation_query(
    reservations: ReservationRepository = Depends(create_reservation_repository),
    store_offers: StoreOffersPort = Depends(create_store_offers_port),
) -> StoreReservationQuery:
    """stores PickupPendingPort와 admin 매장 확인을 둘 다 만족하는 읽기 전용 질의 (D-34)."""
    return StoreReservationQuery(reservations=reservations, store_offers=store_offers, clock=_reservations_clock)


def create_store_reservation_list_service(
    reservations: ReservationRepository = Depends(create_reservation_repository),
    stores: StoreQueryService = Depends(create_store_query_service),  # StoreOwnerPort를 구조적으로 만족
    store_offers: StoreOffersPort = Depends(create_store_offers_port),
) -> StoreReservationListService:
    """상점주용 예약 목록 조회(읽기 전용, R-REQ24·25)."""
    return StoreReservationListService(
        reservations=reservations, stores=stores, store_offers=store_offers
    )


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
    auth: AuthApplicationService = Depends(create_auth_service),  # 같은 요청 세션
) -> PaymentApplicationService:
    return PaymentApplicationService(
        session=session,
        reservations=reservations,
        payments=payments,
        refunds=refunds,
        auth=auth,
        gateway=_payments_gateway,
        clock=_payments_clock,
    )


def create_reservation_refund_port(
    payments: PaymentApplicationService = Depends(create_payment_service),
) -> RefundPort:
    """예약용 RefundPort. 위쪽 예약 구역의 create_refund_port를 옮기지 않고, wire_dependencies에서 이 함수로 override한다."""
    return PaymentRefundAdapter(payments)


# ── admin ────────────────────────────
def create_reservation_admin(
    service: ReservationApplicationService = Depends(create_reservation_service),
    query: StoreReservationQuery = Depends(create_store_reservation_query),
) -> ReservationAdminPort:
    return ReservationAdminAdapter(service, query)  # 같은 요청 세션의 예약 서비스 (R13)


def create_reservation_admin_for_admin(
    service: ReservationApplicationService = Depends(create_reservation_service),
    query: StoreReservationQuery = Depends(create_store_reservation_query),
) -> ReservationAdminPort:
    """관리자 강제 탈퇴용: 예약 취소·환불 사유는 고정 문구(관리자 원문 사유는 탈퇴 기록에만)."""
    return AdminWithdrawalReservationAdapter(service, query)


# ── auth 탈퇴 조정 (모듈 간 연결: stores·catalog·reservations 팩토리 뒤에 정의) ──
def create_account_withdrawal_service(
    session: AsyncSession = Depends(get_db),
    accounts: AuthApplicationService = Depends(create_auth_service),
    stores: StoresApplicationService = Depends(create_stores_service),
    offers: CatalogApplicationService = Depends(create_catalog_service),
    reservations: ReservationAdminPort = Depends(create_reservation_admin),
) -> AccountWithdrawalService:
    # 포트는 auth가 정의(auth.application.ports), 기존 서비스·어댑터가 구조적으로 만족한다 (R11)
    return AccountWithdrawalService(
        session=session,
        accounts=accounts,
        stores=stores,
        offers=offers,
        reservations=reservations,
        clock=_auth_clock,
    )


def create_admin_service(
    session: AsyncSession = Depends(get_db),
    accounts: AuthApplicationService = Depends(create_auth_service),
    stores: StoresApplicationService = Depends(create_stores_service),
    offers: CatalogApplicationService = Depends(create_catalog_service),
    reservations: ReservationAdminPort = Depends(create_reservation_admin_for_admin),
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
            provide_password_reset_service: create_password_reset_service,
            provide_withdrawal_service: create_account_withdrawal_service,
            provide_store_repository: create_store_repository,
            provide_stores_service: create_stores_service,
            provide_store_query_service: create_store_query_service,
            provide_store_port: create_store_port,
            provide_catalog_service: create_catalog_service,
            provide_reservation_lookup: create_catalog_reservation_lookup,
            provide_reservation_cancel: create_catalog_reservation_canceller,
            provide_reservation_service: create_reservation_service,
            provide_reservation_lifecycle_service: create_reservation_lifecycle_service,
            provide_store_reservation_list_service: create_store_reservation_list_service,
            provide_admin_service: create_admin_service,
            provide_payment_service: create_payment_service,
            # 중첩 Depends도 override가 적용된다: create_reservation_service가 받는 RefundPort를 결제 어댑터로 교체
            create_refund_port: create_reservation_refund_port,
            # catalog 서비스가 받는 포트도 같은 방식으로 교체 (정의 순서 때문에 위쪽 함수를 옮기지 않는다)
            create_reservation_lookup: create_catalog_reservation_lookup,
            create_reservation_cancel: create_catalog_reservation_canceller,
            # stores 서비스가 받는 PickupPendingPort를 예약 질의로 교체 (D-36)
            create_pickup_pending_port: create_store_reservation_query,
        }
    )
