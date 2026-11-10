import uuid
from abc import ABC, abstractmethod

from payments.domain.payment import Payment


class PaymentRepository(ABC):
    @abstractmethod
    async def find_by_id(self, payment_id: uuid.UUID, for_update: bool = False) -> Payment | None: ...

    @abstractmethod
    async def find_by_reservation_id(
        self, reservation_id: uuid.UUID, for_update: bool = False
    ) -> Payment | None: ...

    @abstractmethod
    async def save(self, payment: Payment) -> Payment: ...
