"""reservations가 외부 모듈에 요구하는 포트. catalog·payments를 import하지 않고 구조적으로 맞춘다 (R11)."""

import uuid
from datetime import datetime
from typing import Protocol

from reservations.application.views import RefundTarget


class OfferTermsInfo(Protocol):
    offer_id: uuid.UUID
    owner_id: uuid.UUID
    store_name: str
    product_name: str
    pickup_address: str
    sale_price: int
    pickup_start: datetime
    pickup_end: datetime


class StockPort(Protocol):
    """재고와 할인 조건. commit하지 않는다 (R13)."""

    async def get_terms(self, offer_id: uuid.UUID, *, for_update: bool = False) -> OfferTermsInfo: ...

    async def reserve(
        self, offer_id: uuid.UUID, quantity: int, *, user_id: uuid.UUID, now: datetime
    ) -> OfferTermsInfo: ...

    async def release(
        self, offer_id: uuid.UUID, quantity: int, *, user_id: uuid.UUID, reason: str
    ) -> bool: ...


class RefundPort(Protocol):
    """결제 모듈. commit하지 않는다 (R13)."""

    async def refund_for_cancelled_reservation(
        self, target: RefundTarget, *, reason: str, waive_penalty: bool = False
    ) -> None: ...

    # 예약이 PENDING_PAYMENT일 때 취소 전에 부르는 읽기 전용 확인(RD-39). 쓰기·commit 없음.
    # 결제가 없거나 PAID가 아니면 반환, PAID면 DataInconsistentError(500).
    async def ensure_no_paid_payment(self, reservation_id: uuid.UUID) -> None: ...

