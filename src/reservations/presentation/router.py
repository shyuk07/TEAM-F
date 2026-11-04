import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from auth.presentation.dependencies import CurrentUser, OwnerUser
from reservations.application.service import ReservationApplicationService
from reservations.domain import rules
from reservations.domain.pickup_reservation import ReservationStatus
from reservations.presentation.dependencies import provide_reservation_service
from reservations.presentation.schemas import (
    PickupRequest,
    PickupResponse,
    ReservationCancelResponse,
    ReservationCreateRequest,
    ReservationCreateResponse,
    ReservationListResponse,
)

router = APIRouter(prefix="/v1", tags=["예약"])

Service = Annotated[ReservationApplicationService, Depends(provide_reservation_service)]
PageParam = Annotated[int, Query(ge=1, description="페이지 (1부터)")]
SizeParam = Annotated[
    int, Query(ge=1, le=rules.LIST_MAX_SIZE, description=f"페이지 크기 (1~{rules.LIST_MAX_SIZE})")
]


@router.post(
    "/reservations",
    response_model=ReservationCreateResponse,
    status_code=201,
    summary="예약 생성",
)
async def create_reservation(body: ReservationCreateRequest, user: CurrentUser, service: Service):
    return await service.create_reservation(user.id, body.offer_id, body.quantity)


@router.get(
    "/users/me/reservations",
    response_model=ReservationListResponse,
    summary="내 예약 목록 조회",
)
async def list_my_reservations(
    user: CurrentUser,
    service: Service,
    status: ReservationStatus | None = None,
    page: PageParam = 1,
    size: SizeParam = rules.LIST_DEFAULT_SIZE,
):
    result = await service.list_my_reservations(user.id, status, page, size)
    return ReservationListResponse(
        reservations=result.items, page=result.page, size=result.size, total=result.total
    )


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ReservationCancelResponse,
    summary="예약 취소",
)
async def cancel_reservation(reservation_id: uuid.UUID, user: CurrentUser, service: Service):
    return await service.cancel_reservation(user.id, reservation_id)


@router.post(
    "/reservations/{reservation_id}/pickup",
    response_model=PickupResponse,
    summary="픽업 완료",
)
async def complete_pickup(
    reservation_id: uuid.UUID, body: PickupRequest, owner: OwnerUser, service: Service
):
    return await service.complete_pickup(owner.id, reservation_id, body.pickup_code)
