import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

TZ = DateTime(timezone=True)


class PickupReservationModel(Base):
    __tablename__ = "pickup_reservations"
    # S-3: schema.sql의 price 컬럼은 매핑하지 않는다. NULL 허용 컬럼은 schema.sql 그대로 둔다(S-2).
    __table_args__ = (CheckConstraint("quantity >= 1", name="ck_reservations_quantity"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discount_offers.id"), index=True
    )
    quantity: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=text("now()"))
    total_price: Mapped[int | None]
    status: Mapped[str | None] = mapped_column(String(20))
    unit_price: Mapped[int | None]
    pickup_code: Mapped[str | None] = mapped_column(String(20))
    cancelled_at: Mapped[datetime | None] = mapped_column(TZ)
    picked_up_at: Mapped[datetime | None] = mapped_column(TZ)
    store_name: Mapped[str | None] = mapped_column(String(150))
    pickup_address: Mapped[str | None] = mapped_column(String(500))
    product_name: Mapped[str | None] = mapped_column(String(200))
