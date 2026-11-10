"""StoreOffersPort 어댑터. catalog 추상 레포지토리만 쓴다 (R11, R12)."""

import uuid

from catalog.domain.repository.discount_offer_repository import DiscountOfferRepository


class CatalogStoreOffersAdapter:
    def __init__(self, offers: DiscountOfferRepository):
        self.offers = offers

    async def list_offer_ids_of_store(
        self, store_id: uuid.UUID, *, for_update: bool = False
    ) -> list[uuid.UUID]:
        return await self.offers.find_ids_by_store(store_id, for_update=for_update)
