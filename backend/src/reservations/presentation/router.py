import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from auth.presentation.dependencies import CurrentUser, SuspendedAllowedOwnerUser
from reservations.application.service import ReservationApplicationService
from reservations.application.store_reservation_service import StoreReservationListService
from reservations.domain import rules
from reservations.domain.exceptions import DataInconsistentError
from reservations.domain.pickup_reservation import ReservationStatus
from reservations.presentation.dependencies import (
    provide_reservation_service,
    provide_store_reservation_list_service,
)
from reservations.presentation.schemas import (
    PickupRequest,
    PickupResponse,
    ReservationCancelResponse,
    ReservationCreateRequest,
    ReservationCreateResponse,
    ReservationListItem,
    ReservationListResponse,
    StoreReservationListResponse,
)

router = APIRouter(prefix="/v1", tags=["예약"])


# 데이터 불일치는 500으로 변환한다(RD-38). 로그·롤백은 서비스가 이미 했으므로 여기서는 응답만 만든다.
# 409 부모(ReservationConflictError)와 별개 클래스라 전역 409 핸들러에 잡히지 않는다.
def _data_inconsistent_response(error: DataInconsistentError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"success": False, "error_code": error.error_code, "message": str(error)},
    )


Service = Annotated[ReservationApplicationService, Depends(provide_reservation_service)]
StoreListService = Annotated[
    StoreReservationListService, Depends(provide_store_reservation_list_service)
]
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
    items = [_my_item(e) for e in result.items]
    return ReservationListResponse(
        reservations=items, page=result.page, size=result.size, total=result.total
    )


@router.get(
    "/reservations/{reservation_id}",
    response_model=ReservationListItem,
    summary="내 예약 한 건 조회",
)
async def get_my_reservation(reservation_id: uuid.UUID, user: CurrentUser, service: Service):
    return _my_item(await service.get_my_reservation(user.id, reservation_id))


def _my_item(e) -> ReservationListItem:
    """내 예약 목록·단건 응답 항목. 할인의 픽업 시간·취소 마감을 함께 담는다."""
    r = e.reservation
    return ReservationListItem(
        id=r.id,
        offer_id=r.offer_id,
        store_name=r.store_name,
        product_name=r.product_name,
        quantity=r.quantity,
        total_price=r.total_price,
        status=str(r.status),
        created_at=r.created_at,
        pickup_code=r.pickup_code,
        pickup_address=r.pickup_address,
        cancelled_by=None if r.cancelled_by is None else str(r.cancelled_by),
        pickup_start=e.pickup_start,
        pickup_end=e.pickup_end,
        cancellable_until=e.cancellable_until,
    )


@router.get(
    "/stores/{store_id}/reservations",
    response_model=StoreReservationListResponse,
    summary="상점주용 매장 예약 목록 조회",
)
async def list_store_reservations(
    store_id: uuid.UUID,
    owner: SuspendedAllowedOwnerUser,  # 정지된 상점주도 본인 매장 조회 가능(픽업 EP와 같음, D-38)
    service: StoreListService,
    status: ReservationStatus | None = None,
    page: PageParam = 1,
    size: SizeParam = rules.LIST_DEFAULT_SIZE,
):
    result = await service.list_store_reservations(owner.id, store_id, status, page, size)
    return StoreReservationListResponse(
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


@router.post(
    "/reservations/{reservation_id}/pickup",
    response_model=PickupResponse,
    summary="픽업 완료",
)
async def complete_pickup(
    reservation_id: uuid.UUID, body: PickupRequest, owner: SuspendedAllowedOwnerUser, service: Service
):
    return await service.complete_pickup(owner.id, reservation_id, body.pickup_code)
