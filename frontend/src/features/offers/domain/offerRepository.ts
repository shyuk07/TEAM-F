import type { NearbyQuery } from './nearbyQuery';
import type { OfferPage } from './offer';
import type { OfferDetail } from './offerDetail';

export interface OfferRepository {
  findNearby(query: NearbyQuery, signal?: AbortSignal): Promise<OfferPage>;
  findById(id: string, signal?: AbortSignal): Promise<OfferDetail>;
}
