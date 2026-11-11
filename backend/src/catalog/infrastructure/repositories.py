import uuid
from collections.abc import Collection, Sequence
from datetime import datetime

from sqlalchemy import BigInteger, ColumnElement, and_, any_, cast, delete, exists, func, literal, not_, or_, select
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from catalog.domain.discount_offer import OPEN_OFFER_STATUSES, DiscountOffer, OfferStatus
from catalog.domain.exceptions import OfferNotFoundError, ProductNotFoundError
from catalog.domain.product import Product
from catalog.domain.repository.discount_offer_repository import DiscountOfferRepository
from catalog.domain.product_image import ProductImage
from catalog.domain.repository.product_image_repository import ProductImageRepository
from catalog.domain.repository.product_repository import ProductRepository
from catalog.domain.repository.stock_log_repository import StockLogRepository
from catalog.domain.search import OfferSort
from catalog.domain.stock_log import StockLog
from catalog.infrastructure.models import (
    DiscountOfferModel,
    ProductImageModel,
    ProductModel,
    StockLogModel,
)


def _id_array(ids: Sequence[uuid.UUID]):
    """id 목록을 배열 바인드 파라미터 하나로 만든다 (asyncpg 파라미터 상한 회피, D74)."""
    return literal(list(ids), ARRAY(UUID(as_uuid=True)))


def _like_pattern(keyword: str) -> str:
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _product_conditions(
    store_ids: Sequence[uuid.UUID], keyword: str | None, category: str | None
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = [
        ProductModel.store_id == any_(_id_array(store_ids)),
        ProductModel.is_active,
    ]
    if category is not None:
        conditions.append(ProductModel.category == category)
    if keyword is not None:
        pat = _like_pattern(keyword)
        conditions.append(
            or_(
                ProductModel.name.ilike(pat, escape="\\"),
                ProductModel.description.ilike(pat, escape="\\"),
            )
        )
    return conditions


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
        is_active: bool | None = None,
        page: int,
        size: int,
    ) -> tuple[list[Product], int]:
        conditions = [ProductModel.store_id == store_id]
        if is_active is not None:
            conditions.append(ProductModel.is_active == is_active)
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

    async def search_store_ids(
        self,
        *,
        store_ids: Sequence[uuid.UUID],
        keyword: str | None,
        category: str | None,
        page: int,
        size: int,
    ) -> tuple[list[uuid.UUID], int]:
        conditions = _product_conditions(store_ids, keyword, category)
        total = (
            await self.session.execute(
                select(func.count(ProductModel.store_id.distinct())).where(*conditions)
            )
        ).scalar_one()
        stmt = (
            select(ProductModel.store_id)
            .where(*conditions)
            .group_by(ProductModel.store_id)
            .order_by(func.array_position(_id_array(store_ids), ProductModel.store_id))
            .offset((page - 1) * size)
            .limit(size)
        )
        return list((await self.session.execute(stmt)).scalars().all()), total

    async def find_matching_in_stores(
        self,
        *,
        store_ids: Sequence[uuid.UUID],
        keyword: str | None,
        category: str | None,
        now: datetime,
    ) -> list[tuple[Product, bool]]:
        O = DiscountOfferModel
        has_offer = exists().where(
            O.product_id == ProductModel.id,
            or_(*[_status_clause(s, now) for s in OPEN_OFFER_STATUSES]),
        )
        stmt = (
            select(ProductModel, has_offer)
            .where(*_product_conditions(store_ids, keyword, category))
            .order_by(ProductModel.name.asc(), ProductModel.id.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [(self._to_domain(m), bool(flag)) for m, flag in rows]

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

    async def find_ids_by_store(
        self, store_id: uuid.UUID, *, for_update: bool = False
    ) -> list[uuid.UUID]:
        stmt = (
            select(DiscountOfferModel.id)
            .join(ProductModel, ProductModel.id == DiscountOfferModel.product_id)
            .where(ProductModel.store_id == store_id)
            .order_by(DiscountOfferModel.id)  # 잠금 순서 고정(교착 방지)
        )
        if for_update:
            stmt = stmt.with_for_update(of=DiscountOfferModel)
        return list((await self.session.execute(stmt)).scalars().all())

    async def find_by_store(
        self,
        store_id: uuid.UUID,
        *,
        statuses: Sequence[OfferStatus],
        now: datetime,
        exposed_only: bool,
        page: int,
        size: int,
    ) -> tuple[list[tuple[DiscountOffer, Product]], int]:
        conditions = [
            ProductModel.store_id == store_id,
            or_(*[_status_clause(s, now) for s in statuses]),
        ]
        if exposed_only:
            conditions.append(ProductModel.is_active.is_(True))
            conditions.append(not_(_status_clause(OfferStatus.SUSPENDED, now)))
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

    async def search_in_stores(
        self,
        *,
        store_ids: Sequence[uuid.UUID],
        status: OfferStatus,
        keyword: str | None,
        category: str | None,
        sort: OfferSort,
        now: datetime,
        page: int,
        size: int,
    ) -> tuple[list[tuple[DiscountOffer, Product]], int]:
        M = DiscountOfferModel
        conditions: list[ColumnElement[bool]] = [
            ProductModel.store_id == any_(_id_array(store_ids)),
            ProductModel.is_active,
            _status_clause(status, now),
        ]
        if category is not None:
            conditions.append(ProductModel.category == category)
        if keyword is not None:
            conditions.append(ProductModel.name.ilike(_like_pattern(keyword), escape="\\"))
        tail = [M.sales_end.asc(), M.id.asc()]
        if sort == OfferSort.DISTANCE:
            order = [func.array_position(_id_array(store_ids), ProductModel.store_id).asc(), *tail]
        elif sort == OfferSort.PRICE:
            order = [M.sale_price.asc(), *tail]
        elif sort == OfferSort.DISCOUNT_RATE:
            rate = cast(ProductModel.original_price - M.sale_price, BigInteger).op("*")(100).op("/")(
                func.nullif(ProductModel.original_price, 0)
            )
            order = [rate.desc().nulls_last(), *tail]
        else:
            order = tail
        total = (
            await self.session.execute(
                select(func.count())
                .select_from(M)
                .join(ProductModel, ProductModel.id == M.product_id)
                .where(*conditions)
            )
        ).scalar_one()
        stmt = (
            select(M, ProductModel)
            .join(ProductModel, ProductModel.id == M.product_id)
            .where(*conditions)
            .order_by(*order)
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


class SqlAlchemyProductImageRepository(ProductImageRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, image: ProductImage) -> ProductImage:
        model = ProductImageModel(
            product_id=image.product_id,
            content_type=image.content_type,
            size_bytes=image.size_bytes,
            data=image.data,
        )
        self.session.add(model)
        await self.session.flush()
        image.id = model.id
        return image

    async def find_by_id(self, product_id: uuid.UUID, image_id: uuid.UUID) -> ProductImage | None:
        stmt = (
            select(ProductImageModel)
            .options(undefer(ProductImageModel.data))
            .where(ProductImageModel.id == image_id, ProductImageModel.product_id == product_id)
        )
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def delete(self, product_id: uuid.UUID, image_id: uuid.UUID) -> bool:
        return await self.delete_many(product_id, [image_id]) > 0

    async def delete_many(self, product_id: uuid.UUID, image_ids: Collection[uuid.UUID]) -> int:
        if not image_ids:
            return 0
        stmt = (
            delete(ProductImageModel)
            .where(ProductImageModel.product_id == product_id, ProductImageModel.id.in_(list(image_ids)))
            .returning(ProductImageModel.id)
        )
        deleted = (await self.session.execute(stmt)).all()
        return len(deleted)

    @staticmethod
    def _to_domain(model: ProductImageModel) -> ProductImage:
        return ProductImage(
            id=model.id,
            product_id=model.product_id,
            content_type=model.content_type,
            data=model.data,
        )
