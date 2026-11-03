import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from catalog.application.ports import StorePort
from catalog.application.views import (
    OfferView,
    Page,
    ProductDetailView,
    StockAdjustResult,
)
from catalog.domain.discount_offer import DiscountOffer, OfferStatus
from catalog.domain.exceptions import (
    NotStoreOwnerError,
    OfferNotFoundError,
    OpenOfferExistsError,
    ProductNotFoundError,
    StoreNotFoundError,
)
from catalog.domain.product import Product
from catalog.domain.repository.discount_offer_repository import DiscountOfferRepository
from catalog.domain.repository.product_repository import ProductRepository
from catalog.domain.repository.stock_log_repository import StockLogRepository
from catalog.domain.service import Clock
from catalog.domain.stock_log import StockLog
from catalog.domain.store_ref import StoreRef


class CatalogApplicationService:
    def __init__(
        self,
        session: AsyncSession,
        stores: StorePort,
        products: ProductRepository,
        offers: DiscountOfferRepository,
        stock_logs: StockLogRepository,
        clock: Clock,
    ):
        self.session = session
        self.stores = stores
        self.products = products
        self.offers = offers
        self.stock_logs = stock_logs
        self.clock = clock

    # ── 내부 헬퍼 ──────────────────────────
    async def _load_store(self, store_id: uuid.UUID) -> StoreRef:
        info = await self.stores.find_store_by_id(store_id)
        if info is None:
            raise StoreNotFoundError()
        return StoreRef.from_info(info)

    async def _get_product(self, product_id: uuid.UUID, for_update: bool = False) -> Product:
        product = await self.products.find_by_id(product_id, for_update=for_update)
        if product is None:
            raise ProductNotFoundError()
        return product

    @staticmethod
    def _offer_view(offer: DiscountOffer, product: Product, store_name: str, now: datetime) -> OfferView:
        return OfferView(
            offer=offer,
            product=product,
            store_name=store_name,
            status=offer.effective_status(now),
            discount_rate=offer.discount_rate(product.original_price),
            is_sold_out=offer.is_sold_out,
        )

    # ── 쓰기 ──────────────────────────────
    async def create_product(self, user_id: uuid.UUID, store_id: uuid.UUID, data: dict) -> Product:
        store = await self._load_store(store_id)
        store.ensure_owner(user_id, "본인 상점에만 상품을 등록할 수 있습니다.")
        store.ensure_can_register("상품")
        product = Product.register(
            store_id=store_id,
            name=data["name"],
            original_price=data["original_price"],
            category=data.get("category"),
            description=data.get("description"),
            product_image=data.get("product_image"),
        )
        await self.products.save(product)
        await self.session.commit()
        return product

    async def update_product(self, user_id: uuid.UUID, product_id: uuid.UUID, changes: dict) -> Product:
        now = self.clock.now()
        product = await self._get_product(product_id, for_update=True)
        store = await self._load_store(product.store_id)
        store.ensure_owner(user_id, "본인 상점의 상품만 수정할 수 있습니다.")
        open_price = None
        if "original_price" in changes:
            open_offer = await self.offers.find_open_by_product(product_id, now)
            open_price = open_offer.sale_price if open_offer else None
        product.apply_changes(changes, open_price)
        await self.products.save(product)
        await self.session.commit()
        return product

    async def deactivate_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> Product:
        now = self.clock.now()
        product = await self._get_product(product_id, for_update=True)
        store = await self._load_store(product.store_id)
        store.ensure_owner(user_id, "본인 상점의 상품만 변경할 수 있습니다.")
        has_open = await self.offers.find_open_by_product(product_id, now) is not None
        product.deactivate(has_open)
        await self.products.save(product)
        await self.session.commit()
        return product

    async def register_offer(self, user_id: uuid.UUID, product_id: uuid.UUID, data: dict) -> OfferView:
        now = self.clock.now()
        product = await self._get_product(product_id, for_update=True)
        store = await self._load_store(product.store_id)
        store.ensure_owner(user_id, "본인 상점의 상품만 할인 등록할 수 있습니다.")
        store.ensure_can_register("할인")
        product.ensure_active_for_offer()
        if await self.offers.find_open_by_product(product_id, now) is not None:
            raise OpenOfferExistsError("이미 진행 중인 할인 판매가 있습니다.")
        offer = self._new_offer(product, data, now)
        await self.offers.save(offer)
        await self.stock_logs.add(StockLog.initial_stock(offer.id, user_id, offer.initial_stock))
        await self.session.commit()
        return self._offer_view(offer, product, store.name, now)

    async def relist_offer(self, user_id: uuid.UUID, offer_id: uuid.UUID, data: dict) -> OfferView:
        now = self.clock.now()
        # 잠금 순서: product -> offer (교착 방지). product_id를 얻으려고 먼저 잠금 없이 읽는다.
        old = await self.offers.find_by_id(offer_id)
        if old is None:
            raise OfferNotFoundError()
        product = await self._get_product(old.product_id, for_update=True)
        old = await self.offers.find_by_id(offer_id, for_update=True)
        if old is None:
            raise OfferNotFoundError()
        store = await self._load_store(product.store_id)
        store.ensure_owner(user_id, "본인 상점의 할인만 재등록할 수 있습니다.")
        store.ensure_can_register("할인")
        old.ensure_relistable()
        product.ensure_active_for_offer()
        # 신규 할인 검증을 기존 할인 중단보다 먼저 한다 (실패 시 기존 건의 상태가 바뀌지 않게)
        new = self._new_offer(product, data, now)
        old.close(now)
        await self.offers.save(old)
        if await self.offers.find_open_by_product(product.id, now) is not None:
            raise OpenOfferExistsError("이미 진행 중인 할인 판매가 있습니다.")
        await self.offers.save(new)
        await self.stock_logs.add(StockLog.initial_stock(new.id, user_id, new.initial_stock))
        await self.session.commit()
        return self._offer_view(new, product, store.name, now)

    async def adjust_stock(
        self, user_id: uuid.UUID, offer_id: uuid.UUID, amount: int, reason: str | None
    ) -> StockAdjustResult:
        now = self.clock.now()
        offer = await self.offers.find_by_id(offer_id, for_update=True)
        if offer is None:
            raise OfferNotFoundError()
        product = await self._get_product(offer.product_id)
        store = await self._load_store(product.store_id)
        store.ensure_owner(user_id, "본인 상점의 재고만 조정할 수 있습니다.")
        offer.adjust_stock(amount, now)
        await self.offers.save(offer)
        log = await self.stock_logs.add(StockLog.manual_adjustment(offer.id, user_id, amount, reason))
        await self.session.commit()
        return StockAdjustResult(offer=offer, status=offer.effective_status(now), log_id=log.id)

    @staticmethod
    def _new_offer(product: Product, data: dict, now: datetime) -> DiscountOffer:
        return DiscountOffer.register(
            original_price=product.original_price,
            product_id=product.id,
            sale_price=data["sale_price"],
            initial_stock=data["initial_stock"],
            sales_start=data.get("sales_start"),
            sales_end=data["sales_end"],
            pickup_start=data["pickup_start"],
            pickup_end=data["pickup_end"],
            now=now,
        )

    # ── 읽기 ──────────────────────────────
    async def list_products(
        self,
        viewer_id: uuid.UUID | None,
        store_id: uuid.UUID,
        category: str | None,
        is_active: bool,
        page: int,
        size: int,
    ) -> Page[Product]:
        store = await self._load_store(store_id)
        if not is_active and not store.is_owned_by(viewer_id):
            raise NotStoreOwnerError("본인 상점의 비활성 상품만 조회할 수 있습니다.")  # D6
        items, total = await self.products.find_by_store(
            store_id, category=category, is_active=is_active, page=page, size=size
        )
        return Page(items=items, page=page, size=size, total=total)

    async def get_product(self, viewer_id: uuid.UUID | None, product_id: uuid.UUID) -> ProductDetailView:
        product = await self._get_product(product_id)
        store = await self._load_store(product.store_id)
        if not product.is_active and not store.is_owned_by(viewer_id):
            raise ProductNotFoundError()  # D7
        return ProductDetailView(product=product, store_name=store.name, pickup_address=store.pickup_address)

    async def list_offers_by_store(
        self, store_id: uuid.UUID, status: OfferStatus, page: int, size: int
    ) -> Page[OfferView]:
        now = self.clock.now()
        store = await self._load_store(store_id)
        rows, total = await self.offers.find_by_store(
            store_id, status=status, now=now, page=page, size=size
        )
        items = [self._offer_view(o, p, store.name, now) for o, p in rows]
        return Page(items=items, page=page, size=size, total=total)

    async def has_open_offers_for_store(self, store_id: uuid.UUID, *, now: datetime | None = None) -> bool:
        current = now if now is not None else self.clock.now()
        return await self.offers.exists_open_by_store(store_id, current)
