export type GeoPoint = { lat: number; lng: number };

export type OfferSort = 'sales_end' | 'distance' | 'discount_rate' | 'price';

export type RadiusKm = 1 | 3 | 5 | 10;

export type NearbyQuery = {
  location: GeoPoint | null;
  radiusKm: RadiusKm;
  sort: OfferSort;
  keyword: string;
  page: number;
  size: number;
};

export const NEARBY_PAGE_SIZE = 20;

export const RADIUS_OPTIONS: readonly RadiusKm[] = [1, 3, 5, 10];

export const DEFAULT_RADIUS_KM: RadiusKm = 3;

export const KEYWORD_MAX_LENGTH = 100;
