from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


# 결제 테이블
class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # TODO: reservations 테이블이 생기면 ForeignKey("reservations.id") 추가
    reservation_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    # TODO: users 테이블이 생기면 ForeignKey("users.id") 추가
    user_id: Mapped[UUID] = mapped_column(index=True)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# 환불 테이블 (결제 1건당 환불 1건)
class RefundModel(Base):
    __tablename__ = "refunds"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    payment_id: Mapped[UUID] = mapped_column(ForeignKey("payments.id"), unique=True, index=True)
    refund_amount: Mapped[int] = mapped_column(Integer)
    penalty_amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
