from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from auth.presentation.dependencies import CurrentUser
from payments.application.service import PaymentApplicationService
from payments.domain.exceptions import (
    IntegrationNotReadyError,
    PaymentConflictError,
    PaymentStateInconsistentError,
)
from payments.presentation.dependencies import provide_payment_service
from payments.presentation.schemas import (
    PaymentCreate,
    PaymentResponse,
    RefundCreate,
    RefundCreatedResponse,
    RefundResponse,
)

router = APIRouter(prefix="/v1")



# TODO: 연동 전 임시 처리. 503 전역 핸들러가 생기면 제거한다 (R6/R7 예외: 공통 에러 형식은 유지).
#       error_handlers.py를 고치지 않는 결정으로 각 라우터가 변환한다(예약 라우터와 같은 방식).
def _not_ready_response(error: IntegrationNotReadyError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"success": False, "error_code": error.error_code, "message": str(error)},
    )


# 데이터 불일치는 500으로 변환한다(RD-38). 로그와 롤백은 서비스가 이미 했으므로 여기서는 응답만 만든다.
# 409 부모(PaymentConflictError)와 별개 클래스라 아래 409 변환에 잡히지 않는다.
def _data_inconsistent_response(error: PaymentStateInconsistentError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"success": False, "error_code": error.error_code, "message": str(error)},
    )


ServiceDep = Annotated[PaymentApplicationService, Depends(provide_payment_service)]


# 400/403/404는 전역 핸들러(src/error_handlers.py)가 처리한다.
# 409(PaymentConflictError)는 팀 결정(C-12)으로 error_handlers.py를 고치지 않고 router에서 변환한다.
# TODO(C-12): 409 전역 핸들러가 생기면 이 변환을 제거한다. (R6/R7 예외)
@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["결제"],
    summary="모의 결제 실행",
)
async def create_payment(body: PaymentCreate, user: CurrentUser, service: ServiceDep):
    try:
        return await service.pay(user.id, body.reservation_id, use_point=body.use_point)
    except PaymentStateInconsistentError as error:
        return _data_inconsistent_response(error)
    except PaymentConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    tags=["결제"],
    summary="결제 상태 조회",
)
async def get_payment(payment_id: UUID, user: CurrentUser, service: ServiceDep):
    return await service.get_payment(user.id, payment_id)


@router.post(
    "/payments/{payment_id}/refunds",
    response_model=RefundCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["환불"],
    summary="환불 요청",
)
async def create_refund(
    payment_id: UUID, body: RefundCreate, user: CurrentUser, service: ServiceDep
):
    try:
        return await service.refund(user.id, payment_id, body.reason)
    except PaymentStateInconsistentError as error:
        return _data_inconsistent_response(error)
    except IntegrationNotReadyError as error:  # TODO: 임시 503 변환 (재고 복구 연동 전)
        return _not_ready_response(error)
    except PaymentConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get(
    "/refunds/{refund_id}",
    response_model=RefundResponse,
    tags=["환불"],
    summary="환불·위약금 내역 조회",
)
async def get_refund(refund_id: UUID, user: CurrentUser, service: ServiceDep):
    return await service.get_refund(user.id, refund_id)
