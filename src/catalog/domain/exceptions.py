"""catalog 도메인 예외. HTTP 변환은 src/error_handlers.py가 한다 (R6)."""


class ProductNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "상품을 찾을 수 없습니다."):
        super().__init__(message)


class OfferNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "할인 판매를 찾을 수 없습니다."):
        super().__init__(message)


class StoreNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "상점을 찾을 수 없습니다."):
        super().__init__(message)


class NotStoreOwnerError(PermissionError):
    """403 FORBIDDEN (메시지는 EP별로 전달)"""

    def __init__(self, message: str = "본인 상점만 이용할 수 있습니다."):
        super().__init__(message)


class StoreNotApprovedError(ValueError):
    error_code = "STORE_NOT_APPROVED"


class StoreClosedError(ValueError):
    error_code = "STORE_CLOSED"


class ProductInactiveError(ValueError):
    error_code = "PRODUCT_INACTIVE"


class OpenOfferExistsError(ValueError):
    error_code = "OFFER_ALREADY_OPEN"


class ProductAlreadyInactiveError(ValueError):
    error_code = "PRODUCT_ALREADY_INACTIVE"


class ProductHasOpenOfferError(ValueError):
    error_code = "PRODUCT_HAS_OPEN_OFFER"


class PickedUpReservationExistsError(ValueError):
    """400 PICKED_UP_RESERVATION_EXISTS (임시 이름)"""

    error_code = "PICKED_UP_RESERVATION_EXISTS"

    def __init__(self, message: str = "픽업 완료된 예약이 있어 처리할 수 없습니다."):
        super().__init__(message)


class OfferClosedError(ValueError):
    error_code = "OFFER_CLOSED"


class InsufficientStockError(ValueError):
    error_code = "INSUFFICIENT_STOCK"


class OfferEndedError(ValueError):
    error_code = "OFFER_ENDED"


class OfferHasReservationsError(ValueError):
    error_code = "OFFER_HAS_RESERVATIONS"


class OfferAlreadyActiveError(ValueError):
    error_code = "OFFER_ALREADY_ACTIVE"


class OfferNotReservableError(ValueError):
    """예약 차감 불가(판매 전·종료·중단·품절). 예약 어댑터가 reservations의 409 OFFER_NOT_RESERVABLE로 번역한다."""

    error_code = "OFFER_NOT_RESERVABLE"

    def __init__(self, message: str = "예약할 수 없는 상품입니다."):
        super().__init__(message)


class OfferOutOfStockError(ValueError):
    """예약 수량이 남은 재고보다 많다. 예약 어댑터가 reservations의 409 OUT_OF_STOCK으로 번역한다."""

    error_code = "OUT_OF_STOCK"

    def __init__(self, message: str = "재고가 부족합니다."):
        super().__init__(message)


class StockRestoreExceedsInitialError(Exception):
    """재고 복구 후 남은 재고가 최초 수량을 넘는다 = 데이터 불일치.

    ValueError·PermissionError·LookupError·RuntimeError를 상속하지 않는다(400/403/404로 잡혀 바뀌는 것을 막는다).
    예약 어댑터가 reservations의 DataInconsistentError(500)로 번역한다.
    """

    def __init__(self, message: str = "복구할 재고가 최초 수량을 넘습니다."):
        super().__init__(message)


class ReservationDataInconsistentError(Exception):
    """예약 일괄 취소 중 예약·결제 데이터 불일치가 발견되었다(500 DATA_INCONSISTENT).

    예약 쪽 어댑터가 reservations의 DataInconsistentError를 이 예외로 번역한다.
    409/400/403/404/RuntimeError 계열을 상속하지 않는다(전역 핸들러에 잡혀 바뀌는 것을 막는다).
    catalog 라우터가 공통 형식의 500으로 바꾼다. 로그·롤백은 예약 서비스가 이미 했다.
    """

    error_code = "DATA_INCONSISTENT"
    default_message = "예약과 결제 상태가 일치하지 않습니다. 관리자에게 문의해 주세요."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)
