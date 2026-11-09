import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from stores.domain.store import StoreStatus


class StoreOpenRequest(BaseModel):
    pickup_address: str = Field(..., max_length=500, description="픽업 주소 (최대 500자)")


class StoreCloseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="상점 ID")
    name: str = Field(..., description="상점명")
    closed_at: datetime = Field(..., description="폐점 시각")


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="상점 ID")
    owner_id: uuid.UUID = Field(..., description="상점주 ID")
    name: str = Field(..., description="상점명 (상점주 상호)")
    pickup_address: str = Field(..., description="픽업 주소")
    latitude: float = Field(..., description="위도")
    longitude: float = Field(..., description="경도")
    created_at: datetime = Field(..., description="생성 시각")
    approval_at: datetime | None = Field(None, description="개설 시각")
    closed_at: datetime | None = Field(None, description="폐점 시각")


class MyStoreResponse(BaseModel):
    """GET /v1/stores/me. 정지·폐점 사유는 노출하지 않는다 (D58)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="상점 ID")
    owner_id: uuid.UUID = Field(..., description="상점주 ID")
    name: str = Field(..., description="상점명")
    pickup_address: str = Field(..., description="픽업 주소")
    latitude: float | None = Field(None, description="위도 (좌표 변환 도입 전 개설 상점은 null)")
    longitude: float | None = Field(None, description="경도 (좌표 변환 도입 전 개설 상점은 null)")
    created_at: datetime = Field(..., description="생성 시각")
    approval_at: datetime | None = Field(None, description="개설 시각")
    closed_at: datetime | None = Field(None, description="폐점 시각")
    status: StoreStatus = Field(..., description="ACTIVE / SUSPENDED / CLOSED")
