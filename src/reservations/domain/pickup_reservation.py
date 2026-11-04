import hmac
import uuid
from datetime import datetime
from enum import StrEnum

from reservations.domain import rules
from reservations.domain.exceptions import (
    NotReservationOwnerError,
    PickupCodeMismatchError,
    ReservationAlreadyCancelledError,
    ReservationAlreadyPickedUpError,
    ReservationNotPaidError,
    ReservationStateError,
)
from reservations.domain.offer_ref import OfferRef


class ReservationStatus(StrEnum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    RESERVED = "RESERVED"
    PICKED_UP = "PICKED_UP"
    CANCELLED = "CANCELLED"


def _aware(value: datetime | None, label: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label}에는 시간대 정보가 필요합니다.")
    return value


def _int(value: int, label: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label}은(는) 정수여야 합니다.")
    if value < minimum:
        raise ValueError(
            "수량은 1개 이상이어야 합니다." if label == "수량" else f"{label}은(는) {minimum} 이상이어야 합니다."
        )
    return value


def _text(value: str, label: str, max_length: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= max_length:
        raise ValueError(f"{label}은(는) 1자 이상 {max_length}자 이하여야 합니다.")
    return value.strip()


def _normalize_code(code: str) -> str:
    code = code.strip()
    return code if rules.PICKUP_CODE_CASE_SENSITIVE else code.upper()


class PickupReservation:
    def __init__(
        self,
        user_id: uuid.UUID,
        offer_id: uuid.UUID,
        quantity: int,
        unit_price: int,
        total_price: int,
        pickup_code: str,
        store_name: str,
        pickup_address: str,
        product_name: str,
        status: ReservationStatus = ReservationStatus.PENDING_PAYMENT,
        created_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        picked_up_at: datetime | None = None,
        id: uuid.UUID | None = None,
    ):
        if user_id is None or offer_id is None:
            raise ValueError("회원과 할인 상품은 필수입니다.")
        self.id = id
        self.user_id = user_id
        self.offer_id = offer_id
        self.quantity = _int(quantity, "수량", 1)
        self.unit_price = _int(unit_price, "단가", 0)
        self.total_price = _int(total_price, "총액", 0)
        if self.total_price != self.unit_price * self.quantity:
            raise ValueError("총액이 단가×수량과 다릅니다.")
        self.status = ReservationStatus(status)
        self.pickup_code = _text(pickup_code, "예약번호", 20)
        self.store_name = _text(store_name, "매장명", 150)
        self.pickup_address = _text(pickup_address, "픽업 주소", 500)
        self.product_name = _text(product_name, "상품명", 200)
        self.created_at = _aware(created_at, "예약 시각")
        self.cancelled_at = _aware(cancelled_at, "취소 시각")
        self.picked_up_at = _aware(picked_up_at, "픽업 시각")
        if (self.cancelled_at is not None) != (self.status == ReservationStatus.CANCELLED):
            raise ValueError("취소 시각은 취소된 예약에만 있어야 합니다.")
        if (self.picked_up_at is not None) != (self.status == ReservationStatus.PICKED_UP):
            raise ValueError("픽업 시각은 픽업 완료된 예약에만 있어야 합니다.")

    @classmethod
    def create(
        cls,
        user_id: uuid.UUID,
        offer: OfferRef,
        quantity: int,
        pickup_code: str,
        now: datetime,
    ) -> "PickupReservation":
        if _aware(now, "현재 시각") is None:
            raise ValueError("현재 시각에는 시간대 정보가 필요합니다.")
        quantity = _int(quantity, "수량", 1)
        return cls(
            user_id=user_id,
            offer_id=offer.offer_id,
            quantity=quantity,
            unit_price=offer.sale_price,
            total_price=offer.sale_price * quantity,
            pickup_code=pickup_code,
            store_name=offer.store_name,
            pickup_address=offer.pickup_address,
            product_name=offer.product_name,
            status=ReservationStatus.PENDING_PAYMENT,
            created_at=now,
        )

    @property
    def is_paid(self) -> bool:
        return self.status == ReservationStatus.RESERVED

    @property
    def is_cancelled(self) -> bool:
        return self.status == ReservationStatus.CANCELLED

    @property
    def is_picked_up(self) -> bool:
        return self.status == ReservationStatus.PICKED_UP

    @property
    def holds_stock(self) -> bool:
        return self.status in (ReservationStatus.PENDING_PAYMENT, ReservationStatus.RESERVED)

    def ensure_owned_by(self, user_id: uuid.UUID, message: str | None = None) -> None:
        if self.user_id != user_id:
            raise NotReservationOwnerError(*([message] if message else []))

    def _raise_terminal(self) -> None:
        if self.status == ReservationStatus.CANCELLED:
            raise ReservationAlreadyCancelledError()
        if self.status == ReservationStatus.PICKED_UP:
            raise ReservationAlreadyPickedUpError()

    def mark_paid(self) -> None:
        if self.status != ReservationStatus.PENDING_PAYMENT:
            self._raise_terminal()
            raise ReservationStateError()
        self.status = ReservationStatus.RESERVED

    def cancel(self, now: datetime) -> None:
        self._raise_terminal()
        if _aware(now, "현재 시각") is None:
            raise ValueError("현재 시각에는 시간대 정보가 필요합니다.")
        self.status = ReservationStatus.CANCELLED
        self.cancelled_at = now

    def pick_up(self, pickup_code: str, now: datetime) -> None:
        """검사 순서: 상태 -> 코드 (D-9)."""
        self._raise_terminal()
        if self.status == ReservationStatus.PENDING_PAYMENT:
            raise ReservationNotPaidError()
        if _aware(now, "현재 시각") is None:
            raise ValueError("현재 시각에는 시간대 정보가 필요합니다.")
        if not isinstance(pickup_code, str) or not hmac.compare_digest(
            _normalize_code(pickup_code).encode(), _normalize_code(self.pickup_code).encode()
        ):
            raise PickupCodeMismatchError()
        self.status = ReservationStatus.PICKED_UP
        self.picked_up_at = now
