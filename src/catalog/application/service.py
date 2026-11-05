import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from catalog.application.ports import (
    ReservationCancelPort,
    ReservationLookupPort,
    StorePort,
)
from catalog.application.views import (
    DeactivateOfferResult,
    OfferDetailView,
    OfferSuspensionView,
    OfferView,
    Page,
    ProductDetailView,
    StockAdjustResult,
)
from catalog.domain.discount_offer import (
    OFFER_NOTICE,
    OPEN_OFFER_STATUSES,
    DiscountOffer,
    OfferStatus,
)
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
        reservations: ReservationLookupPort,
        reservation_cancel: ReservationCancelPort,
    ):
        self.session = session
        self.stores = stores
        self.products = products
        self.offers = offers
        self.stock_logs = stock_logs
        self.clock = clock
        self.reservations = reservations
        self.reservation_cancel = reservation_cancel

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

    # ── 읽기 ──────────────────────────────
    async def get_offer_detail(
        self, viewer_id: uuid.UUID | None, offer_id: uuid.UUID
    ) -> OfferDetailView:
        now = self.clock.now()
        found = await self.offers.find_with_product(offer_id)
        if found is None:
            raise OfferNotFoundError()
        offer, product = found
        info = await self.stores.find_store_by_id(product.store_id)
        if info is None:
            raise OfferNotFoundError()  # 명세 §10·D56: 404는 "할인 판매를 찾을 수 없습니다." 하나
        store = StoreRef.from_info(info)
        # D17·D20: 정지된 상점·정지된 할인은 소유자 외 404. 명세 D56대로 404 문구는 하나다.
        is_owner = store.is_owned_by(viewer_id)
        if not store.is_visible_to(viewer_id) or not offer.is_visible(now, viewer_is_owner=is_owner):
            raise OfferNotFoundError()
        return OfferDetailView(
            view=self._offer_view(offer, product, store.name, now),
            description=product.description,
            product_image=list(product.product_image),
            pickup_address=store.pickup_address,
            latitude=store.latitude,
            longitude=store.longitude,
            notice=OFFER_NOTICE,
            cancel_policy=offer.cancel_policy(),
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

    async def deactivate_offer(
        self,
        user_id: uuid.UUID,
        offer_id: uuid.UUID,
        reason: str,
        cancel_reservations: bool,
    ) -> DeactivateOfferResult:
        now = self.clock.now()
        # 잠금 순서: product -> offer (relist·update와 같은 패턴). product_id를 얻으려고 먼저 잠금 없이 읽는다.
        old = await self.offers.find_by_id(offer_id)
        if old is None:
            raise OfferNotFoundError()
        product = await self._get_product(old.product_id, for_update=True)
        offer = await self.offers.find_by_id(offer_id, for_update=True)
        if offer is None:
            raise OfferNotFoundError()
        store = await self._load_store(product.store_id)
        store.ensure_owner(user_id, "본인 상점의 할인만 중단할 수 있습니다.")  # 폐점 상점 허용(Q14)
        offer.close(now)  # 이미 중단이면 포트 호출 전에 막는다
        cancelled = 0
        if cancel_reservations:
            cancelled = await self.reservation_cancel.cancel_all_for_offer(offer.id, reason=reason)
        await self.offers.save(offer)
        await self.session.commit()
        return DeactivateOfferResult(
            view=self._offer_view(offer, product, store.name, now),
            cancelled_reservation_count=cancelled,
        )

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

    async def update_offer(self, user_id: uuid.UUID, offer_id: uuid.UUID, changes: dict) -> OfferView:
        now = self.clock.now()
        # 잠금 순서: product -> offer (relist와 같은 패턴)
        old = await self.offers.find_by_id(offer_id)
        if old is None:
            raise OfferNotFoundError()
        product = await self._get_product(old.product_id, for_update=True)
        offer = await self.offers.find_by_id(offer_id, for_update=True)
        if offer is None:
            raise OfferNotFoundError()
        store = await self._load_store(product.store_id)
        store.ensure_owner(user_id, "본인 상점의 할인만 수정할 수 있습니다.")
        delta = 0
        if changes == {"is_active": False}:
            offer.pause(now)
        elif changes == {"is_active": True}:
            store.ensure_not_closed("할인을 재개")
            has_other = await self.offers.find_open_by_product(product.id, now) is not None
            offer.resume(now, product_active=product.is_active, has_other_open_offer=has_other)
        else:
            has_res = await self.reservations.has_reservations_for_offer(offer.id)
            delta = offer.apply_changes(
                changes, original_price=product.original_price, has_reservations=has_res, now=now
            )
        await self.offers.save(offer)
        if delta != 0:
            await self.stock_logs.add(StockLog.offer_edit(offer.id, user_id, delta))
        await self.session.commit()
        return self._offer_view(offer, product, store.name, now)

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
        store.ensure_visible_to(viewer_id)
        if not is_active and not store.is_owned_by(viewer_id):
            raise NotStoreOwnerError("본인 상점의 비활성 상품만 조회할 수 있습니다.")  # D6
        items, total = await self.products.find_by_store(
            store_id, category=category, is_active=is_active, page=page, size=size
        )
        return Page(items=items, page=page, size=size, total=total)

    async def get_product(self, viewer_id: uuid.UUID | None, product_id: uuid.UUID) -> ProductDetailView:
        product = await self._get_product(product_id)
        store = await self._load_store(product.store_id)
        store.ensure_visible_to(viewer_id)
        if not product.is_active and not store.is_owned_by(viewer_id):
            raise ProductNotFoundError()  # D7
        return ProductDetailView(product=product, store_name=store.name, pickup_address=store.pickup_address)

    async def list_offers_by_store(
        self,
        viewer_id: uuid.UUID | None,
        store_id: uuid.UUID,
        statuses: Sequence[OfferStatus] | None,
        page: int,
        size: int,
    ) -> Page[OfferView]:
        now = self.clock.now()
        store = await self._load_store(store_id)
        store.ensure_visible_to(viewer_id)
        selected = tuple(dict.fromkeys(statuses)) if statuses else OPEN_OFFER_STATUSES
        rows, total = await self.offers.find_by_store(
            store_id, statuses=selected, now=now, page=page, size=size
        )
        items = [self._offer_view(o, p, store.name, now) for o, p in rows]
        return Page(items=items, page=page, size=size, total=total)

    async def has_open_offers_for_store(self, store_id: uuid.UUID, *, now: datetime | None = None) -> bool:
        current = now if now is not None else self.clock.now()
        return await self.offers.exists_open_by_store(store_id, current)

    # ── 관리자용 (admin 모듈이 OfferAdminPort로 호출, admin.md 5.2·5.3) ──
    async def suspend_offer(
        self, offer_id: uuid.UUID, reason: str, *, now: datetime, commit: bool = True
    ) -> OfferSuspensionView:
        # 잠금 순서: product -> offer (D34). product_id를 얻으려고 먼저 잠금 없이 읽는다.
        old = await self.offers.find_by_id(offer_id)
        if old is None:
            raise OfferNotFoundError()
        product = await self._get_product(old.product_id, for_update=True)
        offer = await self.offers.find_by_id(offer_id, for_update=True)
        if offer is None:
            raise OfferNotFoundError()
        offer.suspend(reason, now)
        await self.offers.save(offer)
        if commit:
            await self.session.commit()
        return OfferSuspensionView(
            id=offer.id,
            store_id=product.store_id,
            title=product.name,
            status=offer.effective_status(now),
            suspended_reason=offer.suspended_reason,
            suspended_at=offer.suspended_at,
        )

    async def end_all_sales_of_store(
        self, store_id: uuid.UUID, *, now: datetime, commit: bool = True
    ) -> int:
        """상점의 진행 중 할인을 모두 종료하고 종료한 수를 돌려준다. 재고·stock_log는 건드리지 않는다 (D18)."""
        await self.products.find_all_by_store_for_update(store_id)  # product -> offer 순서 (D34)
        offers = await self.offers.find_open_by_store_for_update(store_id, now)
        ended = 0
        for offer in offers:
            if offer.end_sale(now):
                await self.offers.save(offer)
                ended += 1
        if commit:
            await self.session.commit()
        return ended
