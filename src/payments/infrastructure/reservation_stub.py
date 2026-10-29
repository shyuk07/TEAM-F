"""[임시] 예약 모듈이 완성되기 전까지 쓰는 메모리 기반 예약 조회.

reservations 모듈이 완성되면 ReservationGateway를 실제로 구현한 클래스로 교체하고
이 파일은 삭제합니다. (교체 위치: payments/presentation/dependencies.py)
"""

from dataclasses import replace
from uuid import UUID

from payments.application.ports import ReservationInfo


# Swagger에서 바로 테스트할 수 있는 데모 데이터
DEMO_CUSTOMER_ID = UUID("00000000-0000-0000-0000-000000000001")
DEMO_OWNER_ID = UUID("00000000-0000-0000-0000-000000000002")
DEMO_RESERVATION_ID = UUID("00000000-0000-0000-0000-0000000000a1")

_reservations: dict[UUID, ReservationInfo] = {
    DEMO_RESERVATION_ID: ReservationInfo(
        id=DEMO_RESERVATION_ID,
        user_id=DEMO_CUSTOMER_ID,
        store_owner_id=DEMO_OWNER_ID,
        total_price=12000,
        status="PENDING_PAYMENT",
    ),
}


class InMemoryReservationGateway:
    async def get(self, reservation_id: UUID) -> ReservationInfo | None:
        return _reservations.get(reservation_id)

    async def mark_paid(self, reservation_id: UUID) -> None:
        reservation = _reservations[reservation_id]
        _reservations[reservation_id] = replace(reservation, status="CONFIRMED")
