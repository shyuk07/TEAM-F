import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from auth.presentation.dependencies import CurrentUser, OwnerUser
from reservations.application.service import ReservationApplicationService
from reservations.domain import rules
from reservations.domain.exceptions import DataInconsistentError, IntegrationNotReadyError
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



# TODO: 연동 전 임시 처리. 503 전역 핸들러가 생기면 제거한다 (R6/R7 예외: 공통 에러 형식은 유지).
def _not_ready_response(error: IntegrationNotReadyError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"success": False, "error_code": error.error_code, "message": str(error)},
    )


# 데이터 불일치는 500으로 변환한다(RD-38). 로그·롤백은 서비스가 이미 했으므로 여기서는 응답만 만든다.
# 409 부모(ReservationConflictError)와 별개 클래스라 전역 409 핸들러에 잡히지 않는다.
def _data_inconsistent_response(error: DataInconsistentError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"success": False, "error_code": error.error_code, "message": str(error)},
    )


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
    try:
        return await service.create_reservation(user.id, body.offer_id, body.quantity)
    except IntegrationNotReadyError as error:  # TODO: 임시 503 변환
        return _not_ready_response(error)


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
    try:
        return await service.cancel_reservation(user.id, reservation_id)
    except DataInconsistentError as error:
        return _data_inconsistent_response(error)
    except IntegrationNotReadyError as error:  # TODO: 임시 503 변환
        return _not_ready_response(error)


@router.post(
    "/reservations/{reservation_id}/pickup",
    response_model=PickupResponse,
    summary="픽업 완료",
)
async def complete_pickup(
    reservation_id: uuid.UUID, body: PickupRequest, owner: OwnerUser, service: Service
):
    return await service.complete_pickup(owner.id, reservation_id, body.pickup_code)
