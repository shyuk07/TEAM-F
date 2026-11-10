from dataclasses import dataclass

from auth.domain.exceptions import InvalidPageError, InvalidUserFilterError
from auth.domain.user import Role, UserStatus

DEFAULT_PAGE = 1
DEFAULT_SIZE = 20
MAX_SIZE = 100
EMAIL_MAX_LENGTH = 255  # users.email VARCHAR(255)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _enum_filter(value: str | None, enum_cls: type, name: str):
    stripped = _blank_to_none(value)
    if stripped is None:
        return None
    try:
        return enum_cls(stripped)  # 대문자 정확 일치
    except ValueError:
        allowed = ", ".join(m.value for m in enum_cls)
        raise InvalidUserFilterError(
            f"{name} 값이 올바르지 않습니다. {allowed} 중 하나여야 합니다."
        ) from None


@dataclass(frozen=True)
class UserListQuery:
    """관리자 회원 목록 조회 조건. 검증·정규화는 create가 한다."""

    role: Role | None
    status: UserStatus | None
    email: str | None  # 사용자가 입력한 글자 그대로의 부분 문자열(와일드카드 이스케이프는 인프라 담당)
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @classmethod
    def create(
        cls,
        *,
        role: str | None = None,
        status: str | None = None,
        email: str | None = None,
        page: int = DEFAULT_PAGE,
        size: int = DEFAULT_SIZE,
    ) -> "UserListQuery":
        if not _is_int(page) or not _is_int(size) or page < 1 or size < 1 or size > MAX_SIZE:
            raise InvalidPageError()
        role_filter = _enum_filter(role, Role, "role")
        status_filter = _enum_filter(status, UserStatus, "status")
        email_filter = _blank_to_none(email)
        if email_filter is not None and len(email_filter) > EMAIL_MAX_LENGTH:
            raise InvalidUserFilterError(f"email 검색어는 {EMAIL_MAX_LENGTH}자 이하여야 합니다.")
        return cls(
            role=role_filter, status=status_filter, email=email_filter, page=page, size=size
        )
