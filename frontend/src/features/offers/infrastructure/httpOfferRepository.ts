import type { NearbyQuery } from '../domain/nearbyQuery';
import type { OfferPage } from '../domain/offer';
import type { OfferRepository } from '../domain/offerRepository';

export class HttpOfferRepository implements OfferRepository {
  findNearby(query: NearbyQuery, signal?: AbortSignal): Promise<OfferPage> {
    void query;
    void signal;
    throw new Error('not implemented: HttpOfferRepository.findNearby');
  }
}
