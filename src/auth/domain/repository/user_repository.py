import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from auth.domain.user import User
from auth.domain.user_list_query import UserListQuery


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
    async def find_all(self, query: UserListQuery, now: datetime) -> list[User]:
        """필터·정렬(created_at, id 오름차순)·페이지를 적용한 회원 목록. 읽기 전용."""

    @abstractmethod
    async def count_all(self, query: UserListQuery, now: datetime) -> int:
        """같은 필터에 맞는 전체 건수(page·size 무시). 읽기 전용."""
