import uuid
from datetime import datetime
from typing import Any

from catalog.domain.exceptions import NotStoreOwnerError, StoreClosedError, StoreNotApprovedError


class StoreRef:
    """stores 컨텍스트에서 받은 값의 읽기 전용 복사본."""

    def __init__(
        self,
        id: uuid.UUID,
        owner_id: uuid.UUID,
        name: str,
        pickup_address: str,
        approved: bool,
        closed: bool,
    ):
        self.id = id
        self.owner_id = owner_id
        self.name = name
        self.pickup_address = pickup_address
        self.approved = approved
        self.closed = closed

    @classmethod
    def from_info(cls, info: Any) -> "StoreRef":
        approval_at: datetime | None = info.approval_at
        closed_at: datetime | None = info.closed_at
        return cls(
            id=info.id,
            owner_id=info.owner_id,
            name=info.name,
            pickup_address=info.pickup_address,
            approved=approval_at is not None,
            closed=closed_at is not None,
        )

    def is_owned_by(self, user_id: uuid.UUID | None) -> bool:
        return user_id is not None and user_id == self.owner_id

    def ensure_owner(self, user_id: uuid.UUID, message: str) -> None:
        if not self.is_owned_by(user_id):
            raise NotStoreOwnerError(message)

    def ensure_can_register(self, what: str) -> None:
        """what: '상품' 또는 '할인'. 검사 순서는 폐점 -> 미승인 (D9)."""
        if self.closed:
            raise StoreClosedError(f"폐점된 상점에서는 {what}을 등록할 수 없습니다.")
        if not self.approved:
            raise StoreNotApprovedError(f"승인되지 않은 상점에는 {what}을 등록할 수 없습니다.")
