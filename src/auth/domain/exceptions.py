class AuthenticationError(Exception):
    """인증 실패 (HTTP 401로 변환)."""

    error_code = "UNAUTHORIZED"
    default_message = "로그인이 필요합니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class InvalidCredentialsError(AuthenticationError):
    error_code = "INVALID_CREDENTIALS"
    default_message = "이메일 또는 비밀번호가 올바르지 않습니다."


class TokenRevokedError(AuthenticationError):
    error_code = "TOKEN_REVOKED"
    default_message = "로그아웃된 토큰입니다."


class EmailDuplicatedError(Exception):
    """이미 가입된 이메일 (HTTP 409로 변환). ValueError를 상속하지 않는다."""

    error_code = "EMAIL_DUPLICATED"
    default_message = "이미 가입된 이메일입니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class UserNotFoundError(LookupError):
    """회원 없음 (HTTP 404 NOT_FOUND로 변환)."""

    default_message = "회원을 찾을 수 없습니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class RoleForbiddenError(PermissionError):
    """역할 권한 없음 (HTTP 403 FORBIDDEN으로 변환)."""

    default_message = "접근 권한이 없습니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class AccountSuspendedError(PermissionError):
    """정지된 계정 (HTTP 403 FORBIDDEN으로 변환, D8)."""

    default_message = "정지된 계정입니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class OwnerNotApprovedError(PermissionError):
    """승인되지 않은 상점주 (HTTP 403 FORBIDDEN으로 변환, D5)."""

    default_message = "승인 대기 중인 상점주 계정입니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class OwnerNotFoundError(LookupError):
    """상점주 없음 (HTTP 404 NOT_FOUND로 변환, D7). 고객·관리자 ID도 같은 응답."""

    default_message = "상점주를 찾을 수 없습니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class _CodedValueError(ValueError):
    """error_code를 가진 400 도메인 예외의 공통 부모."""

    error_code = "VALIDATION_ERROR"
    default_message = "요청이 올바르지 않습니다."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.default_message)


class OwnerNotPendingError(_CodedValueError):
    error_code = "OWNER_NOT_PENDING"
    default_message = "승인 대기 중인 상점주가 아닙니다."


class InvalidSuspensionEndError(_CodedValueError):
    error_code = "INVALID_SUSPENSION_END"
    default_message = "정지 종료 시각은 현재 이후여야 합니다."


class UserAlreadySuspendedError(_CodedValueError):
    error_code = "USER_ALREADY_SUSPENDED"
    default_message = "이미 정지된 회원입니다."


class UserWithdrawnError(_CodedValueError):
    error_code = "USER_WITHDRAWN"
    default_message = "탈퇴한 회원입니다."


class AdminAccountProtectedError(_CodedValueError):
    error_code = "ADMIN_ACCOUNT_PROTECTED"
    default_message = "관리자 계정은 변경할 수 없습니다."


class UserNotSuspendableError(_CodedValueError):
    """명세에 없는 에러 (D36)."""

    error_code = "USER_NOT_SUSPENDABLE"
    default_message = "승인된 회원만 정지할 수 있습니다."


class UserAlreadyWithdrawnError(_CodedValueError):
    error_code = "USER_ALREADY_WITHDRAWN"
    default_message = "이미 탈퇴한 회원입니다."


class InvalidPageError(_CodedValueError):
    error_code = "INVALID_PAGE"
    default_message = "페이지 값이 올바르지 않습니다."
