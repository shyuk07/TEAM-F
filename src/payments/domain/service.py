from abc import ABC, abstractmethod
from datetime import datetime

from payments.domain.gateway_result import GatewayResult
from payments.domain.payment import Payment


class PaymentGateway(ABC):
    @abstractmethod
    async def charge(self, payment: Payment) -> GatewayResult: ...


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """항상 timezone이 있는 현재 시각(UTC)"""
