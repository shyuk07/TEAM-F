from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from payments.application.ports import CurrentUser
from payments.application.service import PaymentApplicationService
from payments.domain.exceptions import PaymentConflictError
from payments.presentation.dependencies import get_current_user, get_payment_service
from payments.presentation.schemas import PaymentCreate, PaymentResponse, RefundResponse

# /api/v1 -> /v1 변경과 JWT 인증 교체는 2차
router = APIRouter(prefix="/api/v1")

UserDep = Annotated[CurrentUser, Depends(get_current_user)]
ServiceDep = Annotated[PaymentApplicationService, Depends(get_payment_service)]


# 400/403/404는 전역 핸들러(src/error_handlers.py)가 처리한다.
# 409(PaymentConflictError)만 전역 핸들러에 없어서(error_handlers.py 수정 금지) 여기서 변환한다.
# HTTPException은 전역 http_error 핸들러가 공통 형식으로 바꾼다. (2차: 409 핸들러 추가 후 제거)
@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["결제"],
    summary="모의 결제 실행",
)
async def create_payment(body: PaymentCreate, user: UserDep, service: ServiceDep):
    try:
        return await service.pay(user.id, body.reservation_id)
    except PaymentConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    tags=["결제"],
    summary="결제 상태 조회",
)
async def get_payment(payment_id: UUID, user: UserDep, service: ServiceDep):
    return await service.get_payment(user.id, payment_id)


@router.get(
    "/refunds/{refund_id}",
    response_model=RefundResponse,
    tags=["환불"],
    summary="환불·위약금 내역 조회",
)
async def get_refund(refund_id: UUID, user: UserDep, service: ServiceDep):
    return await service.get_refund(user.id, refund_id)
