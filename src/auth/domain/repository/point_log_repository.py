import uuid
from abc import ABC, abstractmethod

from auth.domain.point_log import PointLog, PointType


class PointLogRepository(ABC):
    @abstractmethod
    async def add(self, log: PointLog) -> PointLog: ...

    @abstractmethod
    async def find_by_user(
        self,
        user_id: uuid.UUID,
        *,
        point_type: PointType | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[PointLog]:
        """최신순(created_at desc, id desc)."""

    @abstractmethod
    async def count_by_user(
        self, user_id: uuid.UUID, *, point_type: PointType | None = None
    ) -> int: ...
