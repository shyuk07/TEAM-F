"""StoreOffersPort 어댑터. catalog 추상 레포지토리만 쓴다 (R11, R12)."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from catalog.domain.repository.discount_offer_repository import DiscountOfferRepository


class CatalogStoreOffersAdapter:
    def __init__(self, offers: DiscountOfferRepository):
        self.offers = offers

    async def list_offer_ids_of_store(
        self, store_id: uuid.UUID, *, for_update: bool = False
    ) -> list[uuid.UUID]:
        return await self.offers.find_ids_by_store(store_id, for_update=for_update)

    async def get_pickup_ends(self, offer_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, datetime]:
        ends: dict[uuid.UUID, datetime] = {}
        for offer_id in offer_ids:  # 결제 완료 예약이 걸린 할인만 넘어오므로 적다
            offer = await self.offers.find_by_id(offer_id)
            if offer is not None:
                ends[offer_id] = offer.pickup_end
        return ends
