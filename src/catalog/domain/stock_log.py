import uuid
from datetime import datetime

MAX_REASON_LENGTH = 200
INITIAL_STOCK_REASON = "최초 입고"
OFFER_EDIT_REASON = "할인 수정"


class StockLog:
    """재고 변경 기록 (append-only). 입고 +, 차감 -."""

    def __init__(
        self,
        offer_id: uuid.UUID,
        amount: int,
        user_id: uuid.UUID | None = None,
        reason: str | None = None,
        created_at: datetime | None = None,
        id: uuid.UUID | None = None,
    ):
        if amount == 0:
            raise ValueError("조정 수량은 0이 될 수 없습니다.")
        if reason is not None:
            reason = reason.strip() or None
        if reason is not None and len(reason) > MAX_REASON_LENGTH:
            raise ValueError("사유는 200자 이하여야 합니다.")
        self.id = id
        self.offer_id = offer_id
        self.user_id = user_id
        self.amount = amount
        self.reason = reason
        self.created_at = created_at

    @classmethod
    def initial_stock(cls, offer_id: uuid.UUID, user_id: uuid.UUID | None, quantity: int) -> "StockLog":
        return cls(offer_id=offer_id, user_id=user_id, amount=quantity, reason=INITIAL_STOCK_REASON)

    @classmethod
    def manual_adjustment(
        cls, offer_id: uuid.UUID, user_id: uuid.UUID | None, amount: int, reason: str | None
    ) -> "StockLog":
        return cls(offer_id=offer_id, user_id=user_id, amount=amount, reason=reason)

    @classmethod
    def offer_edit(cls, offer_id: uuid.UUID, user_id: uuid.UUID | None, amount: int) -> "StockLog":
        return cls(offer_id=offer_id, user_id=user_id, amount=amount, reason=OFFER_EDIT_REASON)
