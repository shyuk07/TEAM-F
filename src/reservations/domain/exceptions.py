class ReservationConflictError(Exception):
    """409. ValueError를 상속하면 400이 되므로 Exception을 상속한다 (D-16)."""

    error_code = "CONFLICT"
    default_message = "요청을 처리할 수 없습니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class ReservationNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "예약 정보를 찾을 수 없습니다."):
        super().__init__(message)


class OfferNotFoundError(LookupError):
    """404 NOT_FOUND (할인 상품 없음)"""

    def __init__(self, message: str = "할인 상품을 찾을 수 없습니다."):
        super().__init__(message)


class NotReservationOwnerError(PermissionError):
    """403 FORBIDDEN"""

    def __init__(self, message: str = "본인 예약만 취소할 수 있습니다."):
        super().__init__(message)


class NotPickupStoreOwnerError(PermissionError):
    """403 FORBIDDEN"""

    def __init__(self, message: str = "해당 매장의 상점주만 픽업 완료 처리할 수 있습니다."):
        super().__init__(message)


class PickupCodeMismatchError(ValueError):
    """400 PICKUP_CODE_MISMATCH"""

    error_code = "PICKUP_CODE_MISMATCH"

    def __init__(self, message: str = "예약번호가 일치하지 않습니다."):
        super().__init__(message)


class PickedUpReservationExistsError(ValueError):
    """400 PICKED_UP_RESERVATION_EXISTS (catalog의 같은 이름 예외와 같은 error_code, D-17)"""

    error_code = "PICKED_UP_RESERVATION_EXISTS"

    def __init__(self, message: str = "픽업 완료된 예약이 있어 처리할 수 없습니다."):
        super().__init__(message)


class ReservationStateError(ReservationConflictError):
    """409 RESERVATION_INVALID_STATE"""

    error_code = "RESERVATION_INVALID_STATE"
    default_message = "처리할 수 없는 예약 상태입니다."


class ReservationAlreadyCancelledError(ReservationStateError):
    """409 RESERVATION_ALREADY_CANCELLED"""

    error_code = "RESERVATION_ALREADY_CANCELLED"
    default_message = "이미 취소된 예약입니다."


class ReservationAlreadyPickedUpError(ReservationStateError):
    """409 RESERVATION_ALREADY_PICKED_UP"""

    error_code = "RESERVATION_ALREADY_PICKED_UP"
    default_message = "이미 픽업 완료된 예약입니다."


class ReservationNotPaidError(ReservationStateError):
    """409 RESERVATION_NOT_PAID"""

    error_code = "RESERVATION_NOT_PAID"
    default_message = "결제가 완료되지 않은 예약입니다."


class OfferNotReservableError(ReservationConflictError):
    """409 OFFER_NOT_RESERVABLE"""

    error_code = "OFFER_NOT_RESERVABLE"
    default_message = "예약할 수 없는 상품입니다."


class OutOfStockError(ReservationConflictError):
    """409 OUT_OF_STOCK"""

    error_code = "OUT_OF_STOCK"
    default_message = "재고가 부족합니다."


class IntegrationNotReadyError(Exception):
    """503. 다른 모듈 연동이 아직 준비되지 않았다.

    ValueError/PermissionError/LookupError/RuntimeError/ReservationConflictError를 상속하지 않는다
    (전역 핸들러에 400/403/404/409로 잡히거나 500으로 새는 것을 막는다).
    예약 라우터가 공통 에러 형식의 503으로 변환한다 (TODO 참고).
    """

    error_code = "INTEGRATION_NOT_READY"

    def __init__(self, message: str = "연동이 아직 준비되지 않았습니다."):
        super().__init__(message)


class StockNotConnectedError(IntegrationNotReadyError):
    """503 STOCK_NOT_CONNECTED (재고 차감 연동 전)"""

    error_code = "STOCK_NOT_CONNECTED"

    def __init__(self, message: str = "재고 연동이 아직 준비되지 않아 예약을 생성할 수 없습니다."):
        super().__init__(message)


class RefundNotConnectedError(IntegrationNotReadyError):
    """503 REFUND_NOT_CONNECTED (환불 연동 전)"""

    error_code = "REFUND_NOT_CONNECTED"

    def __init__(
        self, message: str = "환불 연동이 아직 준비되지 않아 결제된 예약은 취소할 수 없습니다."
    ):
        super().__init__(message)
