from dataclasses import dataclass
from datetime import datetime

from auth.domain.user import Role, User, UserStatus

EMAIL_KEYWORD_MAX_LENGTH = 255


@dataclass(frozen=True)
class UserSearchCriteria:
    """관리자 회원 목록 검색 조건. 상태는 effective_status(now) 기준이다.

    SQL 조건은 infrastructure `SqlAlchemyUserRepository._status_conditions`와 한 쌍이다.
    """

    role: Role | None = None
    status: UserStatus | None = None
    email_keyword: str | None = None

    @classmethod
    def of(
        cls, role: Role | None, status: UserStatus | None, email_keyword: str | None
    ) -> "UserSearchCriteria":
        keyword = None
        if email_keyword is not None:
            keyword = User.normalize_email(email_keyword)
            if len(keyword) > EMAIL_KEYWORD_MAX_LENGTH:
                raise ValueError(f"검색어는 {EMAIL_KEYWORD_MAX_LENGTH}자 이하여야 합니다.")
            if any(ord(c) < 32 or ord(c) == 127 for c in keyword):
                raise ValueError("검색어에 사용할 수 없는 문자가 있습니다.")
            keyword = keyword or None
        return cls(role=role, status=status, email_keyword=keyword)

    def matches(self, user: User, now: datetime) -> bool:
        if self.role is not None and user.role is not self.role:
            return False
        if self.status is not None and user.effective_status(now) is not self.status:
            return False
        if self.email_keyword is not None and self.email_keyword not in user.email.lower():
            return False
        return True
