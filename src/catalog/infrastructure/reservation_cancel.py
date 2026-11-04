import uuid


class NoReservationCancel:
    """임시: reservations 구현 전용. reservations 어댑터로 교체할 것(CI-11).

    ReservationCancelPort(application/ports.py)를 구조적으로 만족한다.
    infrastructure는 application을 import할 수 없어 상속하지 않는다 (R2).
    예약 모델이 없으므로 취소할 예약도, 픽업 완료 예약도 없다.
    """

    async def cancel_all_for_offer(self, offer_id: uuid.UUID, *, reason: str) -> int:
        return 0
