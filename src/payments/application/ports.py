"""결제 서비스가 바깥 기능에 기대하는 '연결 지점(인터페이스)' 모음.

결제 서비스는 아래 Protocol에만 의존한다.
실제 구현(예약 모듈, 결제 게이트웨이)은 나중에 갈아끼울 수 있다.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from uuid import UUID

from payments.domain.gateway_result import GatewayResult
from payments.domain.payment import Payment
from payments.domain.reservation_snapshot import ReservationSnapshot


# [임시] 사용자 역할 / 로그인 사용자: 2차에서 auth의 CurrentUser로 교체한다.
# 결제·환불 규칙에서는 역할을 쓰지 않는다(본인 여부만 확인).
class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    OWNER = "OWNER"
    ADMIN = "ADMIN"


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    role: UserRole


class ReservationPort(Protocol):
    """예약 모듈과의 연결 지점. reservations 모듈이 완성되면 실제 어댑터로 교체한다."""

    async def get(
        self, reservation_id: UUID, *, for_update: bool = False
    ) -> ReservationSnapshot | None: ...

    # 결제 성공 시 예약 상태 변경. commit=False로 불리고 서비스가 마지막에 한 번 commit한다.
    async def mark_paid(self, reservation_id: UUID, *, commit: bool = False) -> None: ...


class PaymentGateway(Protocol):
    async def charge(self, payment: Payment) -> GatewayResult: ...
