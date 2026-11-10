import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from catalog.domain.exceptions import (
    NotStoreOwnerError,
    StoreClosedError,
    StoreNotApprovedError,
    StoreNotFoundError,
    StoreSuspendedError,
)


@dataclass(frozen=True)
class ProductListScope:
    is_empty: bool  # True면 조회하지 않고 빈 목록
    is_active: bool | None  # None이면 노출·숨김 모두


class StoreRef:
    """stores 컨텍스트에서 받은 값의 읽기 전용 복사본.

    정지 상점은 등록(#7)·재등록(#13)·재개(#11 is_active:true)가 막히고, 중단·#12·재고 조정은 허용된다 (D86).
    """

    def __init__(
        self,
        id: uuid.UUID,
        owner_id: uuid.UUID,
        name: str,
        pickup_address: str,
        approved: bool,
        closed: bool,
        latitude: float | None = None,
        longitude: float | None = None,
        suspended: bool = False,
    ):
        self.id = id
        self.owner_id = owner_id
        self.name = name
        self.pickup_address = pickup_address
        self.latitude = latitude
        self.longitude = longitude
        self.approved = approved
        self.closed = closed
        # 상태 우선순위 CLOSED > SUSPENDED > ACTIVE (admin.md D16): 폐점된 상점은 정지로 보지 않는다.
        self.suspended = suspended and not closed

    @classmethod
    def from_info(cls, info: Any) -> "StoreRef":
        approval_at: datetime | None = info.approval_at
        closed_at: datetime | None = info.closed_at
        suspended_at: datetime | None = info.suspended_at
        return cls(
            id=info.id,
            owner_id=info.owner_id,
            name=info.name,
            pickup_address=info.pickup_address,
            latitude=info.latitude,
            longitude=info.longitude,
            approved=approval_at is not None,
            closed=closed_at is not None,
            suspended=suspended_at is not None and closed_at is None,
        )

    def is_owned_by(self, user_id: uuid.UUID | None) -> bool:
        return user_id is not None and user_id == self.owner_id

    def ensure_owner(self, user_id: uuid.UUID, message: str) -> None:
        if not self.is_owned_by(user_id):
            raise NotStoreOwnerError(message)

    def is_visible_to(self, viewer_id: uuid.UUID | None) -> bool:
        """정지된 상점은 소유자에게만 보인다 (admin.md D17)."""
        return not self.suspended or self.is_owned_by(viewer_id)

    def ensure_visible_to(self, viewer_id: uuid.UUID | None) -> None:
        if not self.is_visible_to(viewer_id):
            raise StoreNotFoundError()

    def are_products_visible_to(self, viewer_id: uuid.UUID | None) -> bool:
        """폐점·정지된 상점의 상품은 소유자에게만 보인다 (requirements 정책 표, CI-15).
        할인 상세(#10)만 is_visible_to(정지만 숨김)를 그대로 쓴다 (D82, D83)."""
        return not (self.closed or self.suspended) or self.is_owned_by(viewer_id)

    def ensure_products_visible_to(self, viewer_id: uuid.UUID | None) -> None:
        if not self.are_products_visible_to(viewer_id):
            raise StoreNotFoundError()

    def product_list_scope(self, viewer_id: uuid.UUID | None, requested: bool | None) -> ProductListScope:
        """상점 상품 목록의 is_active 필터 해석 (D106). 비소유자의 숨김 조회는 빈 목록."""
        if self.is_owned_by(viewer_id):
            return ProductListScope(is_empty=False, is_active=requested)
        if requested is False:
            return ProductListScope(is_empty=True, is_active=True)
        return ProductListScope(is_empty=False, is_active=True)

    def ensure_can_register(self, what: str) -> None:
        """what: '상품' 또는 '할인'. 검사 순서는 폐점 -> 정지 -> 미승인 (D9, admin.md D17)."""
        if self.closed:
            raise StoreClosedError(f"폐점된 상점에서는 {what}을 등록할 수 없습니다.")
        if self.suspended:
            raise StoreSuspendedError("관리자에 의해 정지된 상점입니다.")
        if not self.approved:
            raise StoreNotApprovedError(f"승인되지 않은 상점에는 {what}을 등록할 수 없습니다.")

    def ensure_not_closed(self, action: str) -> None:
        """이미 등록된 대상에 대한 동작용. 미승인·정지는 검사하지 않는다 (할인 재개는 ensure_can_resume, D86)."""
        if self.closed:
            raise StoreClosedError(f"폐점된 상점에서는 {action}할 수 없습니다.")

    def ensure_can_resume(self) -> None:
        """할인 재개(#11 is_active:true)용. 검사 순서는 폐점 -> 정지. 미승인은 검사하지 않는다 (D86)."""
        if self.closed:
            raise StoreClosedError("폐점된 상점에서는 할인을 재개할 수 없습니다.")
        if self.suspended:
            raise StoreSuspendedError("관리자에 의해 정지된 상점입니다.")
