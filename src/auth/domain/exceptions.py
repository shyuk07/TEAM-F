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
