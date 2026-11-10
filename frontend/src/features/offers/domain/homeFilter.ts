import {
  DEFAULT_RADIUS_KM,
  type GeoPoint,
  type NearbyQuery,
  type OfferSort,
  type RadiusKm,
} from './nearbyQuery';

export type HomeFilter = { sort: OfferSort; radiusKm: RadiusKm; keyword: string };

export const DEFAULT_HOME_FILTER: HomeFilter = {
  sort: 'sales_end',
  radiusKm: DEFAULT_RADIUS_KM,
  keyword: '',
};

export const SORT_OPTIONS: readonly { sort: OfferSort; label: string }[] = [
  { sort: 'sales_end', label: '마감 임박' },
  { sort: 'distance', label: '가까운 순' },
  { sort: 'discount_rate', label: '할인율' },
  { sort: 'price', label: '낮은 가격' },
];

export function readHomeFilter(search: string): HomeFilter {
  void search;
  throw new Error('not implemented: readHomeFilter');
}

export function toHomeSearch(filter: HomeFilter): string {
  void filter;
  throw new Error('not implemented: toHomeSearch');
}

export function isSortAvailable(sort: OfferSort, hasLocation: boolean): boolean {
  void sort;
  void hasLocation;
  throw new Error('not implemented: isSortAvailable');
}

export function effectiveSort(sort: OfferSort, hasLocation: boolean): OfferSort {
  void sort;
  void hasLocation;
  throw new Error('not implemented: effectiveSort');
}

export function nextRadius(r: RadiusKm): RadiusKm | null {
  void r;
  throw new Error('not implemented: nextRadius');
}

export function locationChipLabel(hasLocation: boolean, r: RadiusKm): string {
  void hasLocation;
  void r;
  throw new Error('not implemented: locationChipLabel');
}

export function locationStatusText(hasLocation: boolean): string {
  void hasLocation;
  throw new Error('not implemented: locationStatusText');
}

export function toNearbyQuery(
  filter: HomeFilter,
  location: GeoPoint | null,
  page: number,
): NearbyQuery {
  void filter;
  void location;
  void page;
  throw new Error('not implemented: toNearbyQuery');
}
