import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, LargeBinary, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

TZ = DateTime(timezone=True)


class ProductModel(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("original_price >= 0", name="ck_products_original_price"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))  # S1: NOT NULL
    category: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    original_price: Mapped[int]  # S1: NOT NULL
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    product_image: Mapped[list | None] = mapped_column(JSON)


class DiscountOfferModel(Base):
    __tablename__ = "discount_offers"
    # S3: schema.sql의 price 컬럼은 매핑하지 않는다.
    __table_args__ = (
        CheckConstraint("sale_price >= 0", name="ck_offer_sale_price"),
        CheckConstraint("initial_stock >= 0", name="ck_offer_initial_stock"),
        CheckConstraint("remaining_stock BETWEEN 0 AND initial_stock", name="ck_offer_remaining_stock"),
        CheckConstraint("pickup_end > pickup_start", name="ck_offer_pickup_window"),
        CheckConstraint(
            "status IN ('SCHEDULED', 'ON_SALE', 'SOLD_OUT', 'CLOSED', 'SUSPENDED')",
            name="ck_offer_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), index=True
    )
    sale_price: Mapped[int]
    initial_stock: Mapped[int]
    remaining_stock: Mapped[int]
    sales_start: Mapped[datetime] = mapped_column(TZ)  # S4: NOT NULL
    sales_end: Mapped[datetime] = mapped_column(TZ)
    pickup_start: Mapped[datetime] = mapped_column(TZ)
    pickup_end: Mapped[datetime] = mapped_column(TZ)
    status: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    suspended_reason: Mapped[str | None] = mapped_column(String(500))  # S11
    suspended_at: Mapped[datetime | None] = mapped_column(TZ)  # S11


class StockLogModel(Base):
    __tablename__ = "stock_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discount_offers.id"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    amount: Mapped[int]
    reason: Mapped[str | None] = mapped_column(String(200))  # S2
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=text("now()"))


class ProductImageModel(Base):
    __tablename__ = "product_images"
    __table_args__ = (
        CheckConstraint(
            "content_type IN ('image/jpeg', 'image/png', 'image/webp')",
            name="ck_product_images_content_type",
        ),
        CheckConstraint("size_bytes BETWEEN 1 AND 5242880", name="ck_product_images_size"),
        CheckConstraint("octet_length(data) = size_bytes", name="ck_product_images_size_matches"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), index=True
    )
    content_type: Mapped[str] = mapped_column(String(20))
    size_bytes: Mapped[int]
    # 실수로 select(ProductImageModel)을 해도 바이트를 읽지 않는다. 비동기에서는 undefer 필수.
    data: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(TZ, server_default=text("now()"))
