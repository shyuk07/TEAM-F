import type { NearbyQuery } from './nearbyQuery';
import type { Offer, OfferList, OfferPage, OfferStatus } from './offer';
import type { OfferDetail } from './offerDetail';

export interface OfferRepository {
  findNearby(query: NearbyQuery, signal?: AbortSignal): Promise<OfferPage>;
  findById(id: string, signal?: AbortSignal): Promise<OfferDetail>;
  findByStore(
    storeId: string,
    statuses: OfferStatus[],
    page: number,
    size: number,
    signal?: AbortSignal,
  ): Promise<OfferList>;
  findOfferById(id: string, signal?: AbortSignal): Promise<Offer>;
}
