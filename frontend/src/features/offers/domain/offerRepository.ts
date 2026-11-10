import type { NearbyQuery } from './nearbyQuery';
import type { OfferPage } from './offer';

// C2 담당이 findById를 더한다(customer-home.md §5.4).
export interface OfferRepository {
  findNearby(query: NearbyQuery, signal?: AbortSignal): Promise<OfferPage>;
}
