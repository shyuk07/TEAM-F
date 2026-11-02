import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

TZ = DateTime(timezone=True)


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("users_point >= 0", name="ck_users_point_nonneg"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(100))
    users_point: Mapped[int] = mapped_column(server_default="0")
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=text("now()"))
    business_number: Mapped[str | None] = mapped_column(Text)


class PointLogModel(Base):
    __tablename__ = "point_log"
    __table_args__ = (
        CheckConstraint(
            "point_type IN ('EARN', 'USE', 'RESTORE', 'REVOKE')", name="ck_point_log_type"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    amount: Mapped[int]
    point_type: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=text("now()"))


class TokenBlacklistModel(Base):
    __tablename__ = "token_blacklist"

    jti: Mapped[str] = mapped_column(Text, primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(TZ, index=True)
