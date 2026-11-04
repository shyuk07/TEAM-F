import uuid


class NoReservationLookup:
    """임시: reservations 구현 전용. reservations 레포지토리 어댑터로 교체할 것(CI-10).

    ReservationLookupPort(application/ports.py)를 구조적으로 만족한다.
    infrastructure는 application을 import할 수 없어 상속하지 않는다 (R2).
    """

    async def has_reservations_for_offer(self, offer_id: uuid.UUID) -> bool:
        return False
