import uuid
from datetime import datetime
from typing import Any

from reservations.domain import rules
from reservations.domain.exceptions import NotPickupStoreOwnerError


class OfferRef:
    """catalog에서 받은 할인 조건의 읽기 전용 복사본 (R11)."""

    def __init__(
        self,
        offer_id: uuid.UUID,
        owner_id: uuid.UUID,
        store_name: str,
        product_name: str,
        pickup_address: str,
        sale_price: int,
        pickup_start: datetime,
        pickup_end: datetime,
        cancellable_until: datetime | None = None,
    ):
        self.offer_id = offer_id
        self.owner_id = owner_id
        self.store_name = store_name
        self.product_name = product_name
        self.pickup_address = pickup_address
        self.sale_price = sale_price
        self.pickup_start = pickup_start
        self.pickup_end = pickup_end
        # 고객 취소·환불 마감 시각. catalog가 계산해 넘긴다(예약 생성 등 마감을 쓰지 않는 경로에서는 없을 수 있다).
        self.cancellable_until = cancellable_until

    @classmethod
    def from_info(cls, info: Any) -> "OfferRef":
        return cls(
            offer_id=info.offer_id,
            owner_id=info.owner_id,
            store_name=info.store_name,
            product_name=info.product_name,
            pickup_address=info.pickup_address,
            sale_price=info.sale_price,
            pickup_start=info.pickup_start,
            pickup_end=info.pickup_end,
            cancellable_until=getattr(info, "cancellable_until", None),
        )

    def is_owned_by(self, user_id: uuid.UUID | None) -> bool:
        return user_id is not None and user_id == self.owner_id

    def ensure_owned_by(self, user_id: uuid.UUID, message: str | None = None) -> None:
        if not self.is_owned_by(user_id):
            raise NotPickupStoreOwnerError(*([message] if message else []))

    def ensure_reservable_by(self, user_id: uuid.UUID) -> None:
        """상점주 자기 매장 예약 금지 규칙 (Q-3). 기본값은 허용이라 아무것도 하지 않는다."""
        if not rules.ALLOW_OWNER_SELF_RESERVATION and self.is_owned_by(user_id):
            raise ValueError("본인 매장의 상품은 예약할 수 없습니다.")

    def ensure_pickup_time(self, now: datetime) -> None:
        """픽업 시간 창 규칙 (Q-5). 기본값은 강제하지 않는다."""
        if rules.PICKUP_WINDOW_ENFORCED and not self.pickup_start <= now <= self.pickup_end:
            raise ValueError("픽업 시간이 아닙니다.")
