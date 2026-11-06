import uuid
from abc import ABC, abstractmethod

from auth.domain.password_reset_code import PasswordResetCode


class PasswordResetCodeRepository(ABC):
    @abstractmethod
    async def find_by_user_id(
        self, user_id: uuid.UUID, for_update: bool = False
    ) -> PasswordResetCode | None: ...

    @abstractmethod
    async def save(self, code: PasswordResetCode) -> PasswordResetCode:
        """회원당 1행. 없으면 INSERT, 있으면 덮어쓴다(재요청은 이전 코드를 무효로 한다). flush까지만."""

    @abstractmethod
    async def delete(self, user_id: uuid.UUID) -> None: ...
