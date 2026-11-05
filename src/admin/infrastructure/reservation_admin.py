import uuid


class NoReservationAdmin:
    """임시 구현 (admin.md B-6, C10, D43). 미연계(R16): 예약을 취소하지 않고 RESERVED 검사는 항상 통과한다.

    reservations 후속 작업이 실제 구현을 만들면 container 바인딩만 교체한다.
    """

    async def cancel_reserved_for_user(self, user_id: uuid.UUID, *, reason: str) -> int:
        return 0

    async def has_reserved_for_store(self, store_id: uuid.UUID) -> bool:
        return False
