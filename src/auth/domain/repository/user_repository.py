import uuid
from abc import ABC, abstractmethod

from auth.domain.user import User


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
