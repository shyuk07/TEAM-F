import uuid
from datetime import datetime

from sqlalchemy import Double, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

TZ = DateTime(timezone=True)


class StoreModel(Base):
    __tablename__ = "stores"
    __table_args__ = (UniqueConstraint("owner_id", name="uq_stores_owner_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    name: Mapped[str] = mapped_column(String(150))
    pickup_address: Mapped[str] = mapped_column(String(500))
    latitude: Mapped[float | None] = mapped_column(Double)
    longitude: Mapped[float | None] = mapped_column(Double)
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=text("now()"))
    approval_at: Mapped[datetime | None] = mapped_column(TZ)
    closed_at: Mapped[datetime | None] = mapped_column(TZ)
