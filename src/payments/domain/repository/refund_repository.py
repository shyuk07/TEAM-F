import uuid
from abc import ABC, abstractmethod

from payments.domain.refund import Refund


class RefundRepository(ABC):
    @abstractmethod
    async def find_by_id(self, refund_id: uuid.UUID) -> Refund | None: ...

    @abstractmethod
    async def find_by_payment_id(self, payment_id: uuid.UUID) -> Refund | None: ...

    @abstractmethod
    async def save(self, refund: Refund) -> Refund: ...
