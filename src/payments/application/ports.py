"""결제 서비스가 바깥 기능에 기대하는 '연결 지점(인터페이스)' 모음.

결제 서비스는 아래 Protocol에만 의존합니다.
실제 구현(DB 저장소, 예약 모듈, 로그인 사용자)은 나중에 갈아끼울 수 있습니다.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from uuid import UUID

from payments.domain.payment import Payment
from payments.domain.refund import Refund


# 사용자 역할 (auth 모듈이 완성되면 그쪽 정의로 교체)
class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    OWNER = "OWNER"
    ADMIN = "ADMIN"


# 로그인한 사용자 정보
@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    role: UserRole


# 결제에 필요한 예약 정보만 추린 것
@dataclass(frozen=True)
class ReservationInfo:
    id: UUID
    user_id: UUID
    store_owner_id: UUID
    total_price: int
    status: str


# 예약 모듈과의 연결 지점 (reservations 모듈이 완성되면 실제 구현으로 교체)
class ReservationGateway(Protocol):
    async def get(self, reservation_id: UUID) -> ReservationInfo | None: ...

    async def mark_paid(self, reservation_id: UUID) -> None: ...


# 결제/환불 저장소
class PaymentRepository(Protocol):
    async def get_payment(self, payment_id: UUID) -> Payment | None: ...

    async def get_payment_by_reservation(self, reservation_id: UUID) -> Payment | None: ...

    async def add_payment(self, payment: Payment) -> None: ...

    async def get_refund(self, refund_id: UUID) -> Refund | None: ...

    # 환불 저장과 결제 상태 변경(REFUNDED)을 한 번에 반영
    async def add_refund(self, refund: Refund, payment: Payment) -> None: ...
