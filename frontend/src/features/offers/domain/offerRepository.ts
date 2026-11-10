import type { NearbyOfferPage } from './offer';
import type { NearbyOfferQuery } from './search';

export interface OfferRepository {
  findNearby(q: NearbyOfferQuery, signal?: AbortSignal): Promise<NearbyOfferPage>;
}
