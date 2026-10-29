from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from payments.application.ports import CurrentUser, UserRole
from payments.application.service import PaymentService
from payments.infrastructure.repositories import SqlAlchemyPaymentRepository
from payments.infrastructure.reservation_stub import InMemoryReservationGateway


# [임시] 로그인 사용자 확인
# auth 모듈의 JWT 인증이 완성되면 그쪽 get_current_user로 교체합니다.
# 그 전까지는 헤더로 사용자를 흉내 냅니다. (예: X-User-Id, X-User-Role: CUSTOMER)
async def get_current_user(
    x_user_id: Annotated[UUID | None, Header()] = None,
    x_user_role: Annotated[UserRole | None, Header()] = None,
) -> CurrentUser:
    if x_user_id is None or x_user_role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다.",
        )
    return CurrentUser(id=x_user_id, role=x_user_role)


async def get_payment_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentService:
    return PaymentService(
        repository=SqlAlchemyPaymentRepository(session),
        # [임시] reservations 모듈이 완성되면 실제 구현으로 교체
        reservations=InMemoryReservationGateway(),
    )
