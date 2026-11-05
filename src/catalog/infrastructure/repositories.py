import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import ColumnElement, and_, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.exceptions import OfferNotFoundError, ProductNotFoundError
from catalog.domain.product import Product
from catalog.domain.repository.discount_offer_repository import DiscountOfferRepository
from catalog.domain.repository.product_repository import ProductRepository
from catalog.domain.repository.stock_log_repository import StockLogRepository
from catalog.domain.stock_log import StockLog
from catalog.infrastructure.models import (
    DiscountOfferModel,
    ProductModel,
    StockLogModel,
)


class SqlAlchemyProductRepository(ProductRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, product_id: uuid.UUID, for_update: bool = False) -> Product | None:
        stmt = select(ProductModel).where(ProductModel.id == product_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_all_by_store_for_update(self, store_id: uuid.UUID) -> list[Product]:
        stmt = (
            select(ProductModel)
            .where(ProductModel.store_id == store_id)
            .order_by(ProductModel.id.asc())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models]

    async def find_by_store(
        self,
        store_id: uuid.UUID,
        *,
        category: str | None = None,
        is_active: bool = True,
        page: int,
        size: int,
    ) -> tuple[list[Product], int]:
        conditions = [ProductModel.store_id == store_id, ProductModel.is_active == is_active]
        if category is not None:
            conditions.append(ProductModel.category == category)
        total = (
            await self.session.execute(select(func.count()).select_from(ProductModel).where(*conditions))
        ).scalar_one()
        stmt = (
            select(ProductModel)
            .where(*conditions)
            .order_by(ProductModel.name.asc(), ProductModel.id.asc())  # D15
            .offset((page - 1) * size)
            .limit(size)
        )
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models], total

    async def save(self, product: Product) -> Product:
        if product.id is None:
            model = ProductModel(
                store_id=product.store_id,
                name=product.name,
                category=product.category,
                description=product.description,
                original_price=product.original_price,
                is_active=product.is_active,
                product_image=list(product.product_image),
            )
            self.session.add(model)
            await self.session.flush()
            product.id = model.id
        else:
            model = await self.session.get(ProductModel, product.id)
            if model is None:
                raise ProductNotFoundError("저장할 상품을 찾을 수 없습니다.")
            model.name = product.name
            model.category = product.category
            model.description = product.description
            model.original_price = product.original_price
            model.is_active = product.is_active
            model.product_image = list(product.product_image)
            await self.session.flush()
        return product

    @staticmethod
    def _to_domain(model: ProductModel) -> Product:
        return Product(
            id=model.id,
            store_id=model.store_id,
            name=model.name,
            category=model.category,
            description=model.description,
            original_price=model.original_price,
            is_active=model.is_active,
            product_image=list(model.product_image or []),
        )


def _status_clause(status: OfferStatus, now: datetime) -> ColumnElement[bool]:
    """DiscountOffer.effective_status와 같은 우선순위의 SQL 조건. now는 항상 인자로 받는다 (CI-5).

    우선순위: CLOSED(비활성) > SUSPENDED > CLOSED(마감 경과) > SCHEDULED > SOLD_OUT > ON_SALE (admin.md C6).
    """
    M = DiscountOfferModel
    if status == OfferStatus.SUSPENDED:
        return and_(M.is_active, M.suspended_at.is_not(None))
    not_suspended = M.suspended_at.is_(None)
    if status == OfferStatus.CLOSED:
        return or_(not_(M.is_active), and_(not_suspended, M.sales_end <= now))
    live = and_(M.is_active, not_suspended, M.sales_end > now)
    if status == OfferStatus.SCHEDULED:
        return and_(live, M.sales_start > now)
    started = and_(live, M.sales_start <= now)
    if status == OfferStatus.SOLD_OUT:
        return and_(started, M.remaining_stock == 0)
    return and_(started, M.remaining_stock > 0)  # ON_SALE


class SqlAlchemyDiscountOfferRepository(DiscountOfferRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, offer_id: uuid.UUID, for_update: bool = False) -> DiscountOffer | None:
        stmt = select(DiscountOfferModel).where(DiscountOfferModel.id == offer_id)
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_with_product(self, offer_id: uuid.UUID) -> tuple[DiscountOffer, Product] | None:
        stmt = (
            select(DiscountOfferModel, ProductModel)
            .join(ProductModel, ProductModel.id == DiscountOfferModel.product_id)
            .where(DiscountOfferModel.id == offer_id)
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            return None
        return self._to_domain(row[0]), SqlAlchemyProductRepository._to_domain(row[1])

    async def find_open_by_product(
        self, product_id: uuid.UUID, now: datetime
    ) -> DiscountOffer | None:
        stmt = (
            select(DiscountOfferModel)
            .where(
                DiscountOfferModel.product_id == product_id,
                DiscountOfferModel.is_active,
                DiscountOfferModel.sales_end > now,
            )
            .order_by(DiscountOfferModel.sales_end.desc(), DiscountOfferModel.id)
            .limit(1)
        )
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def find_open_by_store_for_update(
        self, store_id: uuid.UUID, now: datetime
    ) -> list[DiscountOffer]:
        stmt = (
            select(DiscountOfferModel)
            .join(ProductModel, ProductModel.id == DiscountOfferModel.product_id)
            .where(
                ProductModel.store_id == store_id,
                DiscountOfferModel.is_active,
                DiscountOfferModel.sales_end > now,
            )
            .order_by(DiscountOfferModel.id.asc())
            .with_for_update(of=DiscountOfferModel)
            .execution_options(populate_existing=True)
        )
        models = (await self.session.execute(stmt)).scalars().all()
        return [self._to_domain(m) for m in models]

    async def exists_open_by_store(self, store_id: uuid.UUID, now: datetime) -> bool:
        stmt = (
            select(DiscountOfferModel.id)
            .join(ProductModel, ProductModel.id == DiscountOfferModel.product_id)
            .where(
                ProductModel.store_id == store_id,
                DiscountOfferModel.is_active,
                DiscountOfferModel.sales_end > now,
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).first() is not None

    async def find_by_store(
        self,
        store_id: uuid.UUID,
        *,
        statuses: Sequence[OfferStatus],
        now: datetime,
        page: int,
        size: int,
    ) -> tuple[list[tuple[DiscountOffer, Product]], int]:
        conditions = [
            ProductModel.store_id == store_id,
            or_(*[_status_clause(s, now) for s in statuses]),
        ]
        base = select(DiscountOfferModel, ProductModel).join(
            ProductModel, ProductModel.id == DiscountOfferModel.product_id
        )
        total = (
            await self.session.execute(
                select(func.count())
                .select_from(DiscountOfferModel)
                .join(ProductModel, ProductModel.id == DiscountOfferModel.product_id)
                .where(*conditions)
            )
        ).scalar_one()
        stmt = (
            base.where(*conditions)
            .order_by(DiscountOfferModel.sales_end.asc(), DiscountOfferModel.id.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            (self._to_domain(o), SqlAlchemyProductRepository._to_domain(p)) for o, p in rows
        ], total

    async def save(self, offer: DiscountOffer) -> DiscountOffer:
        if offer.id is None:
            model = DiscountOfferModel(
                product_id=offer.product_id,
                sale_price=offer.sale_price,
                initial_stock=offer.initial_stock,
                remaining_stock=offer.remaining_stock,
                sales_start=offer.sales_start,
                sales_end=offer.sales_end,
                pickup_start=offer.pickup_start,
                pickup_end=offer.pickup_end,
                status=str(offer.status),
                is_active=offer.is_active,
                suspended_reason=offer.suspended_reason,
                suspended_at=offer.suspended_at,
            )
            self.session.add(model)
            await self.session.flush()
            offer.id = model.id
        else:
            model = await self.session.get(DiscountOfferModel, offer.id)
            if model is None:
                raise OfferNotFoundError("저장할 할인 판매를 찾을 수 없습니다.")
            model.sale_price = offer.sale_price
            model.sales_start = offer.sales_start
            model.sales_end = offer.sales_end
            model.pickup_start = offer.pickup_start
            model.pickup_end = offer.pickup_end
            model.initial_stock = offer.initial_stock
            model.remaining_stock = offer.remaining_stock
            model.status = str(offer.status)
            model.is_active = offer.is_active
            model.suspended_reason = offer.suspended_reason
            model.suspended_at = offer.suspended_at
            await self.session.flush()
        return offer

    @staticmethod
    def _to_domain(model: DiscountOfferModel) -> DiscountOffer:
        return DiscountOffer(
            id=model.id,
            product_id=model.product_id,
            sale_price=model.sale_price,
            initial_stock=model.initial_stock,
            remaining_stock=model.remaining_stock,
            sales_start=model.sales_start,
            sales_end=model.sales_end,
            pickup_start=model.pickup_start,
            pickup_end=model.pickup_end,
            status=OfferStatus(model.status),
            is_active=model.is_active,
            suspended_reason=model.suspended_reason,
            suspended_at=model.suspended_at,
        )


class SqlAlchemyStockLogRepository(StockLogRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, log: StockLog) -> StockLog:
        model = StockLogModel(
            offer_id=log.offer_id, user_id=log.user_id, amount=log.amount, reason=log.reason
        )
        self.session.add(model)
        await self.session.flush()
        log.id = model.id
        log.created_at = model.created_at
        return log
