import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255, description="이메일. 중복 불가")
    password: str = Field(..., min_length=1, max_length=128, description="비밀번호 (8자 이상)")
    name: str | None = Field(None, max_length=100, description="이름 (상점주는 상호)")
    phone: str | None = Field(None, max_length=100, description="전화번호")
    role: str = Field(..., description="CUSTOMER 또는 OWNER (ADMIN 입력 불가)")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="회원 ID")
    email: str = Field(..., description="이메일")
    name: str | None = Field(None, description="이름")
    phone: str | None = Field(None, description="전화번호")
    role: str = Field(..., description="역할")
    users_point: int = Field(..., description="포인트 잔액")
    created_at: datetime = Field(..., description="가입 시각")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT 액세스 토큰")
    token_type: str = Field("bearer", description="토큰 유형")


class PointLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="내역 ID")
    amount: int = Field(..., description="변동량 (적립 +, 사용 -)")
    point_type: str = Field(..., description="EARN / USE / RESTORE / REVOKE")
    created_at: datetime = Field(..., description="발생 시각")


class PointLogListResponse(BaseModel):
    users_point: int = Field(..., description="포인트 잔액")
    logs: list[PointLogResponse] = Field(..., description="최신순 내역")
    page: int = Field(..., description="페이지 (0부터)")
    size: int = Field(..., description="페이지 크기")
    total_elements: int = Field(..., description="전체 건수")
