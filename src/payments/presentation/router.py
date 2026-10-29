from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from payments.application.ports import CurrentUser
from payments.application.service import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    PaymentError,
    PaymentService,
)
from payments.presentation.dependencies import get_current_user, get_payment_service
from payments.presentation.schemas import PaymentCreate, PaymentResponse, RefundResponse


router = APIRouter(prefix="/api/v1")

UserDep = Annotated[CurrentUser, Depends(get_current_user)]
ServiceDep = Annotated[PaymentService, Depends(get_payment_service)]


# 서비스 예외 -> HTTP 상태 코드
def _to_http_error(error: PaymentError) -> HTTPException:
    status_codes = {
        NotFoundError: status.HTTP_404_NOT_FOUND,
        ForbiddenError: status.HTTP_403_FORBIDDEN,
        ConflictError: status.HTTP_409_CONFLICT,
    }
    return HTTPException(
        status_code=status_codes.get(type(error), status.HTTP_400_BAD_REQUEST),
        detail=str(error),
    )


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["결제"],
    summary="모의 결제 실행",
)
async def create_payment(body: PaymentCreate, user: UserDep, service: ServiceDep):
    try:
        return await service.pay(user, body.reservation_id)
    except PaymentError as error:
        raise _to_http_error(error) from error


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    tags=["결제"],
    summary="결제 상태 조회",
)
async def get_payment(payment_id: UUID, user: UserDep, service: ServiceDep):
    try:
        return await service.get_payment(user, payment_id)
    except PaymentError as error:
        raise _to_http_error(error) from error


@router.get(
    "/refunds/{refund_id}",
    response_model=RefundResponse,
    tags=["환불"],
    summary="환불·위약금 내역 조회",
)
async def get_refund(refund_id: UUID, user: UserDep, service: ServiceDep):
    try:
        return await service.get_refund(user, refund_id)
    except PaymentError as error:
        raise _to_http_error(error) from error
