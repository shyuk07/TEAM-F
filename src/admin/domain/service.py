from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    """admin 도메인에는 엔티티가 없다. 규칙은 소유 컨텍스트에 있고 admin은 시각만 필요하다 (D31)."""

    @abstractmethod
    def now(self) -> datetime:
        """항상 timezone이 있는 현재 시각(UTC)"""
