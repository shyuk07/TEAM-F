import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# 값 검증(빈 사유, 1 미만 금액)은 도메인이 명세 문구로 낸다. 길이·범위 제약을 두지 않는다 (D26).
class ReasonRequest(BaseModel):
    reason: str = Field(..., description="사유")


class UserSuspendRequest(BaseModel):
    reason: str = Field(..., description="정지 사유")
    suspended_until: datetime | None = Field(None, description="정지 종료 시각. 없으면 무기한")


class PointGrantRequest(BaseModel):
    amount: int = Field(..., description="지급 포인트(1 이상)")
    reason: str = Field(..., description="지급 사유")


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OwnerApprovalResponse(_FromAttributes):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    status: str
    approved_at: datetime | None


class OwnerRejectionResponse(_FromAttributes):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    status: str
    rejected_reason: str | None
    rejected_at: datetime | None


class UserSuspensionResponse(_FromAttributes):
    id: uuid.UUID
    email: str
    role: str
    status: str
    suspended_reason: str | None
    suspended_at: datetime | None
    suspended_until: datetime | None


class UserWithdrawalResponse(_FromAttributes):
    id: uuid.UUID
    status: str
    deleted_at: datetime | None
    cancelled_reservation_count: int = Field(..., description="취소한 RESERVED 예약 수")


class StoreSuspensionResponse(_FromAttributes):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    status: str
    suspended_reason: str | None
    suspended_at: datetime | None


class StoreClosureResponse(_FromAttributes):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    status: str
    closed_reason: str | None
    closed_at: datetime | None


class OfferSuspensionResponse(_FromAttributes):
    id: uuid.UUID
    store_id: uuid.UUID
    title: str = Field(..., description="상품명")
    status: str
    suspended_reason: str | None
    suspended_at: datetime | None


class PointHistoryItemResponse(_FromAttributes):
    id: uuid.UUID | None
    amount: int
    type: str = Field(..., validation_alias="point_type", description="EARN/USE/RESTORE/REVOKE/GRANT")
    reason: str | None
    balance_after: int | None
    created_by: uuid.UUID | None
    created_at: datetime | None


class PointHistoryPageResponse(_FromAttributes):
    user_id: uuid.UUID
    balance: int
    history: list[PointHistoryItemResponse]
    page: int
    size: int
    total: int


class UserListItemResponse(_FromAttributes):
    id: uuid.UUID
    email: str
    name: str | None
    role: str
    status: str = Field(
        ...,
        description="PENDING / APPROVED / REJECTED / SUSPENDED / WITHDRAWN (기간이 지난 정지는 APPROVED)",
    )
    created_at: datetime = Field(..., description="가입 시각")


class UserPageResponse(_FromAttributes):
    items: list[UserListItemResponse]
    page: int
    size: int
    total: int = Field(..., description="필터에 맞는 전체 건수")


class PointGrantResponse(_FromAttributes):
    id: uuid.UUID | None
    user_id: uuid.UUID
    amount: int
    type: str = Field(..., validation_alias="point_type")
    reason: str | None
    balance_after: int | None
    created_by: uuid.UUID | None
    created_at: datetime | None
