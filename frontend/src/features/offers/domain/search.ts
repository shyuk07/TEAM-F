import { formatRadiusKm } from './locationSheet';
import type { NearbyOffer, NearbyOfferPage } from './offer';

export type GeoPoint = { lat: number; lng: number };

export type SearchArea = { point: GeoPoint; radiusKm: number };

export const DEFAULT_RADIUS_KM = 3;
export const WIDEN_RADIUS_KM = 5;
export const PAGE_SIZE = 20;
export const KEYWORD_MAX_LENGTH = 100;

export type OfferSortKey = 'sales_end' | 'distance' | 'discount_rate' | 'price';

export const SORT_CHIPS: readonly { key: OfferSortKey; label: string }[] = [
  { key: 'sales_end', label: '마감 임박' },
  { key: 'distance', label: '가까운 순' },
  { key: 'discount_rate', label: '할인율' },
  { key: 'price', label: '낮은 가격' },
];

export const DEFAULT_SORT: OfferSortKey = 'sales_end';

export type NearbyOfferQuery = {
  area: SearchArea | null;
  keyword: string | undefined;
  sort: OfferSortKey;
  page: number;
  size: number;
};

export type LocationStatus = 'locating' | 'located' | 'unavailable';

export function isSortSelectable(key: OfferSortKey, hasLocation: boolean): boolean {
  return key !== 'distance' || hasLocation;
}

export function resolveSort(key: OfferSortKey, hasLocation: boolean): OfferSortKey {
  return isSortSelectable(key, hasLocation) ? key : DEFAULT_SORT;
}

export function normalizeKeyword(raw: string): string | undefined {
  const trimmed = raw.trim();
  if (trimmed === '') return undefined;
  return trimmed.slice(0, KEYWORD_MAX_LENGTH);
}

export function queryKey(q: Omit<NearbyOfferQuery, 'page'>): string {
  const area = q.area === null ? '' : `${q.area.point.lat}|${q.area.point.lng}|${q.area.radiusKm}`;
  return [area, q.keyword ?? '', q.sort, q.size].join('#');
}

export function hasNextPage(p: NearbyOfferPage): boolean {
  return p.page * p.size < p.total;
}

export function appendPage(prev: NearbyOffer[], next: NearbyOffer[]): NearbyOffer[] {
  const seen = new Set(prev.map((o) => o.offer.id));
  return [...prev, ...next.filter((o) => !seen.has(o.offer.id))];
}

// TODO: 임시 문구다(빈 목록(검색어 있음), 오류, 「더 보기」, 더 보기 실패, 위치 칩 라벨).
//   왜: screens.md·content.md에 C1 목록 상태 문구가 없다 (docs/design/frontend/offers.md D-20, D-21, D-23, D-32)
//   언제: 결정 후 (디자인 시스템: content.md C1 문구 확정)
export function locationChipLabel(status: LocationStatus, radiusKm: number): string {
  if (status === 'located') return `내 주변 · ${formatRadiusKm(radiusKm)}`;
  return status === 'locating' ? '위치 확인 중' : '위치 없음';
}
