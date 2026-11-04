"""payments 도메인 예외.

HTTP 상태 코드 변환은 src/error_handlers.py 전역 핸들러가 한다.
- LookupError 하위 -> 404 NOT_FOUND
- PermissionError 하위 -> 403 FORBIDDEN
- ValueError 하위 -> 400 (클래스의 error_code)
- PaymentConflictError 하위 -> 409 (ValueError를 상속하면 400이 되므로 Exception을 상속)
  409는 전역 핸들러에 아직 없어서 router가 HTTPException(409)로 바꾼다. (2차에서 핸들러로 이동)

400/409 구분 규칙: 상태가 맞지 않아 아예 할 수 없다 = 400, 이미 처리되어 중복이다 = 409.
"""


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
