import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from admin.application.service import AdminApplicationService
from admin.presentation.dependencies import provide_admin_service
from admin.presentation.schemas import (
    OfferSuspensionResponse,
    OwnerApprovalResponse,
    OwnerRejectionResponse,
    PointGrantRequest,
    PointGrantResponse,
    PointHistoryPageResponse,
    ReasonRequest,
    StoreClosureResponse,
    StoreSuspensionResponse,
    UserSuspendRequest,
    UserSuspensionResponse,
    UserWithdrawalResponse,
)
from auth.presentation.dependencies import AdminUser

# 기존 auth 관리자 EP(GET /users/{id}, POST /token-blacklist/purge)와 경로가 겹쳐도 메서드가 달라 충돌 없음 (D42, B-11)
ADMIN_PREFIX = "/v1/admin"
TAGS = ["관리자"]

router = APIRouter(prefix=ADMIN_PREFIX)

Service = Annotated[AdminApplicationService, Depends(provide_admin_service)]


@router.patch(
    "/owners/{owner_id}/approve",
    response_model=OwnerApprovalResponse,
    tags=TAGS,
    summary="상점주 계정 승인",
)
async def approve_owner(owner_id: uuid.UUID, admin: AdminUser, service: Service):
    return await service.approve_owner(owner_id)


@router.patch(
    "/owners/{owner_id}/reject",
    response_model=OwnerRejectionResponse,
    tags=TAGS,
    summary="상점주 계정 거부",
)
async def reject_owner(owner_id: uuid.UUID, body: ReasonRequest, admin: AdminUser, service: Service):
    return await service.reject_owner(owner_id, body.reason)


@router.patch(
    "/users/{user_id}/suspend",
    response_model=UserSuspensionResponse,
    tags=TAGS,
    summary="회원 정지",
)
async def suspend_user(
    user_id: uuid.UUID, body: UserSuspendRequest, admin: AdminUser, service: Service
):
    return await service.suspend_user(user_id, body.reason, body.suspended_until)


@router.delete(
    "/users/{user_id}",
    response_model=UserWithdrawalResponse,
    tags=TAGS,
    summary="회원 강제 탈퇴",
)
async def withdraw_user(user_id: uuid.UUID, body: ReasonRequest, admin: AdminUser, service: Service):
    return await service.withdraw_user(user_id, body.reason)


@router.patch(
    "/stores/{store_id}/suspend",
    response_model=StoreSuspensionResponse,
    tags=TAGS,
    summary="상점 정지",
)
async def suspend_store(store_id: uuid.UUID, body: ReasonRequest, admin: AdminUser, service: Service):
    return await service.suspend_store(store_id, body.reason)


@router.patch(
    "/stores/{store_id}/close",
    response_model=StoreClosureResponse,
    tags=TAGS,
    summary="상점 강제 폐점",
)
async def close_store(store_id: uuid.UUID, body: ReasonRequest, admin: AdminUser, service: Service):
    return await service.close_store(store_id, body.reason)


@router.patch(
    "/offers/{offer_id}/suspend",
    response_model=OfferSuspensionResponse,
    tags=TAGS,
    summary="할인 상품 정지",
)
async def suspend_offer(offer_id: uuid.UUID, body: ReasonRequest, admin: AdminUser, service: Service):
    return await service.suspend_offer(offer_id, body.reason)


# page/size 범위는 Query 제약이 아니라 서비스(auth)가 명세 문구(INVALID_PAGE)로 검증한다 (6.3절)
@router.get(
    "/users/{user_id}/points",
    response_model=PointHistoryPageResponse,
    tags=TAGS,
    summary="회원 포인트 잔액·이력 조회",
)
async def get_user_points(
    user_id: uuid.UUID, admin: AdminUser, service: Service, page: int = 1, size: int = 20
):
    return await service.get_user_points(user_id, page, size)


@router.post(
    "/users/{user_id}/points",
    response_model=PointGrantResponse,
    status_code=status.HTTP_201_CREATED,
    tags=TAGS,
    summary="회원 포인트 지급",
)
async def grant_points(
    user_id: uuid.UUID, body: PointGrantRequest, admin: AdminUser, service: Service
):
    return await service.grant_points(admin.id, user_id, body.amount, body.reason)
