"""payments 도메인 예외.

HTTP 상태 코드 변환은 src/error_handlers.py 전역 핸들러가 한다.
- LookupError 하위 -> 404 NOT_FOUND
- PermissionError 하위 -> 403 FORBIDDEN
- ValueError 하위 -> 400 (클래스의 error_code)
- PaymentConflictError 하위 -> 409 (ValueError를 상속하면 400이 되므로 Exception을 상속)
  409는 전역 핸들러에 아직 없어서 router가 HTTPException(409)로 바꾼다. (2차에서 핸들러로 이동)
- PaymentStateInconsistentError -> 500 DATA_INCONSISTENT (Exception 직접 상속, router가 변환)

400/409 구분 규칙: 상태가 맞지 않아 아예 할 수 없다 = 400, 이미 처리되어 중복이다 = 409.
"""

from enum import StrEnum
from uuid import UUID


# ---------- 404 ----------
class PaymentNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "결제 정보를 찾을 수 없습니다."):
        super().__init__(message)


class RefundNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "환불 정보를 찾을 수 없습니다."):
        super().__init__(message)


class ReservationNotFoundError(LookupError):
    """404 NOT_FOUND"""

    def __init__(self, message: str = "예약 정보를 찾을 수 없습니다."):
        super().__init__(message)


# ---------- 403 ----------
class PaymentAccessDeniedError(PermissionError):
    """403 FORBIDDEN (결제 요청·조회 권한 없음)"""

    def __init__(self, message: str = "결제 정보에 접근할 권한이 없습니다."):
        super().__init__(message)


class RefundAccessDeniedError(PermissionError):
    """403 FORBIDDEN (환불 요청·조회 권한 없음)"""

    def __init__(self, message: str = "환불 정보에 접근할 권한이 없습니다."):
        super().__init__(message)


# ---------- 400 ----------
class ReservationNotPayableError(ValueError):
    """400 RESERVATION_NOT_PAYABLE"""

    error_code = "RESERVATION_NOT_PAYABLE"

    def __init__(self, message: str = "결제할 수 없는 예약입니다."):
        super().__init__(message)


class PaymentNotRefundableError(ValueError):
    """400 PAYMENT_NOT_REFUNDABLE"""

    error_code = "PAYMENT_NOT_REFUNDABLE"

    def __init__(self, message: str = "환불할 수 없는 결제입니다."):
        super().__init__(message)


class InvalidPaymentTransitionError(ValueError):
    """400 INVALID_PAYMENT_STATE"""

    error_code = "INVALID_PAYMENT_STATE"

    def __init__(self, message: str = "허용되지 않는 결제 상태 변경입니다."):
        super().__init__(message)


class PaymentFailedError(ValueError):
    """400 PAYMENT_FAILED (게이트웨이 결제 실패)"""

    error_code = "PAYMENT_FAILED"

    def __init__(self, message: str = "결제에 실패했습니다."):
        super().__init__(message)


# ---------- 409 ----------
class PaymentConflictError(Exception):
    """409 공통 부모. ValueError를 상속하면 400이 되므로 Exception을 상속한다."""

    error_code = "PAYMENT_CONFLICT"

    def __init__(self, message: str = "요청이 현재 상태와 충돌합니다."):
        super().__init__(message)


class PaymentAlreadyExistsError(PaymentConflictError):
    """409 PAYMENT_ALREADY_EXISTS (이미 결제된 예약)"""

    error_code = "PAYMENT_ALREADY_EXISTS"

    def __init__(self, message: str = "이미 결제된 예약입니다."):
        super().__init__(message)


class PaymentAlreadyRefundedError(PaymentConflictError):
    """409 PAYMENT_ALREADY_REFUNDED (이미 환불 처리된 결제)"""

    error_code = "PAYMENT_ALREADY_REFUNDED"

    def __init__(self, message: str = "이미 환불 처리된 결제입니다."):
        super().__init__(message)


# ---------- 500 ----------
class InconsistencyKind(StrEnum):
    """데이터 불일치 종류. 로그에 남기는 값이다(개인정보 없음)."""

    PAYMENT_MISSING = "PAYMENT_MISSING"  # 예약은 결제 완료(RESERVED)인데 결제 기록이 없음
    PAYMENT_ALREADY_REFUNDED = "PAYMENT_ALREADY_REFUNDED"  # 예약은 결제 완료인데 결제가 이미 REFUNDED
    PAYMENT_NOT_PAID = "PAYMENT_NOT_PAID"  # 예약은 결제 완료인데 결제가 PAID가 아님(READY/FAILED)
    REFUND_ROW_WITH_PAID_PAYMENT = "REFUND_ROW_WITH_PAID_PAYMENT"  # 환불 행이 있는데 결제가 PAID
    RESERVATION_STATUS_NOT_REFUNDABLE = "RESERVATION_STATUS_NOT_REFUNDABLE"  # 환불 대상 예약 상태가 아님
    PAID_PAYMENT_ON_PENDING_RESERVATION = "PAID_PAYMENT_ON_PENDING_RESERVATION"  # 예약 PENDING_PAYMENT + 결제 PAID
    PAID_PAYMENT_ON_CANCELLED_RESERVATION = "PAID_PAYMENT_ON_CANCELLED_RESERVATION"  # 예약 CANCELLED + 결제 PAID


class PaymentStateInconsistentError(Exception):
    """500 DATA_INCONSISTENT. 예약과 결제 상태가 어긋난 데이터 불일치(RD-38, D-29).

    409 부모(PaymentConflictError)와 ValueError·PermissionError·LookupError·RuntimeError를 상속하지 않는다.
    다른 핸들러에 400/403/404/409로 잡혀 바뀌는 것을 막기 위해서다. 라우터가 500으로 변환한다.
    메시지에는 ID를 넣지 않는다(ID는 속성으로만 들고 있고, 로그에만 남는다).
    """

    error_code = "DATA_INCONSISTENT"
    default_message = "예약과 결제 상태가 일치하지 않습니다. 관리자에게 문의해 주세요."

    def __init__(
        self,
        kind: InconsistencyKind,
        reservation_id: UUID | None = None,
        payment_id: UUID | None = None,
    ):
        super().__init__(self.default_message)
        self.kind = kind
        self.reservation_id = reservation_id
        self.payment_id = payment_id


# ---------- 503 ----------
class IntegrationNotReadyError(Exception):
    """503. 다른 모듈 연동이 준비되지 않았다. 400/403/404/409로 잡히지 않도록 일반 Exception을 상속한다.

    payments 라우터가 공통 에러 형식의 503으로 바꾼다(error_handlers.py는 수정하지 않는 결정).
    """

    error_code = "INTEGRATION_NOT_READY"

    def __init__(self, message: str = "연동이 아직 준비되지 않았습니다."):
        super().__init__(message)


class StockNotConnectedError(IntegrationNotReadyError):
    """503 STOCK_NOT_CONNECTED (재고 복구 연동 전). 예약 모듈의 같은 이름 예외를 어댑터가 번역한 것."""

    error_code = "STOCK_NOT_CONNECTED"

    def __init__(
        self,
        message: str = "재고 연동이 아직 준비되지 않아 결제된 예약의 취소·환불을 처리할 수 없습니다.",
    ):
        super().__init__(message)
