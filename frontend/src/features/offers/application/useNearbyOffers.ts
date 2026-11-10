import type { HomeFilter } from '../domain/homeFilter';
import type { GeoPoint } from '../domain/nearbyQuery';
import type { NearbyOffer } from '../domain/offer';

export type NearbyOffersState = {
  status: 'loading' | 'success' | 'empty' | 'error';
  items: NearbyOffer[];
  total: number;
  hasMore: boolean;
  loadingMore: boolean;
  loadMoreFailed: boolean;
  loadMore(): void;
  retry(): void;
};

export function useNearbyOffers(
  filter: HomeFilter,
  location: GeoPoint | null,
  ready: boolean,
): NearbyOffersState {
  void filter;
  void location;
  void ready;
  throw new Error('not implemented: useNearbyOffers');
}
