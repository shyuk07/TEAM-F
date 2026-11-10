import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

from reservations.domain.offer_ref import OfferRef
from reservations.domain.pickup_reservation import PickupReservation

T = TypeVar("T")


@dataclass(frozen=True)
class ReservationView:
    reservation: PickupReservation
    offer: OfferRef


@dataclass(frozen=True)
class RefundTarget:
    """환불 포트에 넘기는 값. status는 취소 전 상태(RESERVED)다."""

    reservation_id: uuid.UUID
    user_id: uuid.UUID
    total_price: int
    pickup_start: datetime
    status: str
    # 고객 취소의 환불 마감 시각. 일괄 취소(위약금 면제)는 시간 제한이 없어 쓰지 않는다.
    cancellable_until: datetime | None = None


@dataclass(frozen=True)
class CancelledReservation:
    reservation: PickupReservation
    refund_target: RefundTarget | None  # 취소 전에 결제된 예약만 값이 있다
    check_paid_payment: bool = False  # 취소 전에 PENDING_PAYMENT였던 예약: PAID 결제가 없는지 확인해야 한다(RD-39)


@dataclass(frozen=True)
class MyReservationEntry:
    """내 예약 목록 한 줄: 예약 + 할인의 픽업 시간·취소 마감(화면 표시용, 프론트엔드 연동 2026-11-10)."""

    reservation: PickupReservation
    pickup_start: datetime
    pickup_end: datetime
    cancellable_until: datetime


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
