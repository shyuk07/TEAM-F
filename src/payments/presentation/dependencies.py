from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from payments.application.ports import CurrentUser, UserRole
from payments.application.reservation_stub import InMemoryReservationPort
from payments.application.service import PaymentApplicationService


# [임시] 로그인 사용자 확인
# auth 모듈의 JWT 인증(CurrentUser)으로 교체하는 것은 2차 작업이다.
# 그 전까지는 헤더로 사용자를 흉내 낸다. (예: X-User-Id, X-User-Role: CUSTOMER)
# 역할은 결제·환불 규칙에서 쓰지 않는다(본인 여부만 확인).
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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PaymentApplicationService:
    # 레포지토리·게이트웨이·정책은 서비스 생성자가 기본값으로 만든다.
    # [임시] reservations 모듈이 완성되면 실제 ReservationPort 어댑터로 교체 (이 한 줄)
    return PaymentApplicationService(db, reservations=InMemoryReservationPort())
