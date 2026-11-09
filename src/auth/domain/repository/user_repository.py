import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from auth.domain.user import User
from auth.domain.user_search import UserSearchCriteria


class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: uuid.UUID, for_update: bool = False) -> User | None: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool: ...

    @abstractmethod
    async def save(self, user: User) -> User:
        """신규(id None)는 INSERT, 기존은 UPDATE. flush까지만. 이메일 중복이면 EmailDuplicatedError."""

    @abstractmethod
    async def find_page(
        self, criteria: UserSearchCriteria, *, now: datetime, offset: int, limit: int
    ) -> list[User]:
        """가입 시각 최신순(created_at DESC, id DESC). 상태 조건은 effective_status(now) 기준. 읽기 전용."""

    @abstractmethod
    async def count_matching(self, criteria: UserSearchCriteria, *, now: datetime) -> int: ...
