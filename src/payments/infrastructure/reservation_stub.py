"""[임시] 예약 모듈이 완성되기 전까지 쓰는 메모리 기반 ReservationPort 구현.

reservations 모듈이 완성되면 실제 어댑터로 교체하고 이 파일은 삭제한다.
(교체 위치: src/container.py의 create_payment_reservation_port)

ReservationPort(application/ports.py)를 구조적으로 만족한다. infrastructure는 application을
import할 수 없어 상속하지 않는다 (R2).
"""

from dataclasses import replace
from uuid import UUID

from payments.domain.reservation_snapshot import ReservationSnapshot
from payments.domain.rules import RESERVATION_PAID_STATUS, RESERVATION_PAYABLE_STATUS

# Swagger에서 바로 테스트할 수 있는 데모 데이터
DEMO_CUSTOMER_ID = UUID("00000000-0000-0000-0000-000000000001")
DEMO_RESERVATION_ID = UUID("00000000-0000-0000-0000-0000000000a1")

_reservations: dict[UUID, ReservationSnapshot] = {
    DEMO_RESERVATION_ID: ReservationSnapshot(
        id=DEMO_RESERVATION_ID,
        user_id=DEMO_CUSTOMER_ID,
        total_price=12000,
        status=RESERVATION_PAYABLE_STATUS,
    ),
}


class InMemoryReservationPort:
    async def get(
        self, reservation_id: UUID, *, for_update: bool = False
    ) -> ReservationSnapshot | None:
        return _reservations.get(reservation_id)

    async def mark_paid(self, reservation_id: UUID, *, commit: bool = False) -> None:
        reservation = _reservations[reservation_id]
        _reservations[reservation_id] = replace(reservation, status=RESERVATION_PAID_STATUS)
