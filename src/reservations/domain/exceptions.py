import uuid
from collections.abc import Iterable
from dataclasses import dataclass


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


class PendingReservationExistsError(ReservationConflictError):
    """409 PENDING_RESERVATION_EXISTS (R-REQ28: 같은 할인 상품의 결제 대기 예약은 회원당 1건)"""

    error_code = "PENDING_RESERVATION_EXISTS"
    default_message = "같은 할인 상품에 결제하지 않은 예약이 이미 있습니다."


class OutOfStockError(ReservationConflictError):
    """409 OUT_OF_STOCK"""

    error_code = "OUT_OF_STOCK"
    default_message = "재고가 부족합니다."


class RefundConflictError(ReservationConflictError):
    """409 REFUND_CONFLICT. 환불 모듈의 충돌 예외를 어댑터가 번역한 것."""

    error_code = "REFUND_CONFLICT"
    default_message = "환불 요청이 현재 상태와 충돌합니다."


@dataclass(frozen=True)
class InconsistencyDetail:
    """불일치 한 건의 기록. 로그에만 쓴다(개인정보 없음). kind는 payments의 불일치 종류 문자열."""

    reservation_id: uuid.UUID | None
    kind: str
    payment_id: uuid.UUID | None = None


class DataInconsistentError(Exception):
    """500 DATA_INCONSISTENT. 예약과 결제 상태가 어긋나 처리를 중단하고 전부 롤백한다(RD-38, RD-39).

    ReservationConflictError(409)·ValueError·PermissionError·LookupError·RuntimeError를 상속하지 않는다
    (전역 핸들러에 409/400/403/404로 잡혀 바뀌는 것을 막는다). 예약 라우터가 500으로 변환한다.
    메시지에는 ID를 넣지 않고, 불일치 목록은 details에만 담는다(일괄 취소는 여러 건).
    """

    error_code = "DATA_INCONSISTENT"
    default_message = "예약과 결제 상태가 일치하지 않습니다. 관리자에게 문의해 주세요."

    def __init__(self, details: Iterable[InconsistencyDetail] = ()):
        super().__init__(self.default_message)
        self.details: tuple[InconsistencyDetail, ...] = tuple(details)

    @property
    def reservation_ids(self) -> tuple[uuid.UUID | None, ...]:
        return tuple(d.reservation_id for d in self.details)
