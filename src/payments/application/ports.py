"""결제 서비스가 바깥 기능에 기대하는 '연결 지점(인터페이스)' 모음.

결제 서비스는 아래 Protocol에만 의존한다.
실제 구현(예약 모듈)은 나중에 갈아끼울 수 있다.
"""

from typing import Protocol
from uuid import UUID

from payments.domain.reservation_snapshot import ReservationSnapshot


class ReservationPort(Protocol):
    """예약 모듈과의 연결 지점. 구현은 reservations.application.adapters(container에서 주입)."""

    async def get(
        self, reservation_id: UUID, *, for_update: bool = False
    ) -> ReservationSnapshot | None: ...

    # 결제 성공 시 예약 상태 변경. commit=False로 불리고 서비스가 마지막에 한 번 commit한다.
    async def mark_paid(self, reservation_id: UUID, *, commit: bool = False) -> None: ...

    # 환불로 예약 취소 + 재고 복구. 이미 취소됐으면 아무것도 하지 않는다(멱등). commit=False로 불린다.
    async def cancel_for_refund(
        self, reservation_id: UUID, reason: str, *, commit: bool = False
    ) -> None: ...
