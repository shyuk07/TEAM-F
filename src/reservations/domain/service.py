from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """항상 timezone이 있는 현재 시각(UTC)"""


class PickupCodeGenerator(ABC):
    @abstractmethod
    def generate(self) -> str:
        """예약번호를 만든다."""
