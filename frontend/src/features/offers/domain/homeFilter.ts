import {
  DEFAULT_RADIUS_KM,
  KEYWORD_MAX_LENGTH,
  NEARBY_PAGE_SIZE,
  RADIUS_OPTIONS,
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

// URL 쿼리(sort·radius·q)에서 홈 필터를 읽는다. 모르는 값은 기본값, 모르는 키는 무시(customer-home.md D-10).
export function readHomeFilter(search: string): HomeFilter {
  const params = new URLSearchParams(search);
  const sortParam = params.get('sort');
  const sort = SORT_OPTIONS.find((o) => o.sort === sortParam)?.sort ?? DEFAULT_HOME_FILTER.sort;
  const radiusParam = Number(params.get('radius'));
  const radiusKm = RADIUS_OPTIONS.find((r) => r === radiusParam) ?? DEFAULT_HOME_FILTER.radiusKm;
  const keyword = (params.get('q') ?? '').trim().slice(0, KEYWORD_MAX_LENGTH);
  return { sort, radiusKm, keyword };
}

// 기본값과 다른 것만 sort·radius·q 순서로 쓴다. 모두 기본이면 ''.
export function toHomeSearch(filter: HomeFilter): string {
  const params = new URLSearchParams();
  if (filter.sort !== DEFAULT_HOME_FILTER.sort) params.set('sort', filter.sort);
  if (filter.radiusKm !== DEFAULT_HOME_FILTER.radiusKm)
    params.set('radius', String(filter.radiusKm));
  if (filter.keyword !== DEFAULT_HOME_FILTER.keyword) params.set('q', filter.keyword);
  const query = params.toString();
  return query === '' ? '' : `?${query}`;
}

// 「가까운 순」은 위치가 있을 때만 쓸 수 있다(400 「distance 정렬은 위치 정보가 필요합니다.」를 미리 막음).
export function isSortAvailable(sort: OfferSort, hasLocation: boolean): boolean {
  return sort !== 'distance' || hasLocation;
}

export function effectiveSort(sort: OfferSort, hasLocation: boolean): OfferSort {
  return isSortAvailable(sort, hasLocation) ? sort : 'sales_end';
}

export function nextRadius(r: RadiusKm): RadiusKm | null {
  const i = RADIUS_OPTIONS.indexOf(r);
  return i >= 0 && i < RADIUS_OPTIONS.length - 1 ? RADIUS_OPTIONS[i + 1] : null;
}

// TODO: 위치 칩에 동네 이름(망원동) 대신 「현재 위치」·「전체 지역」을 쓴다.
//   왜: 좌표 → 동네 이름 변환 API가 없다 (docs/design/frontend/customer-home.md C-2, D-16)
//   언제: 결정 후 (백엔드: 고객용 주소 변환)
export function locationChipLabel(hasLocation: boolean, r: RadiusKm): string {
  return hasLocation ? `현재 위치 · ${r}km` : '전체 지역';
}

export function locationStatusText(hasLocation: boolean): string {
  return hasLocation ? '지금: 현재 위치' : '지금: 전체 지역';
}

export function toNearbyQuery(
  filter: HomeFilter,
  location: GeoPoint | null,
  page: number,
): NearbyQuery {
  return {
    location,
    radiusKm: filter.radiusKm,
    sort: effectiveSort(filter.sort, location !== null),
    keyword: filter.keyword,
    page,
    size: NEARBY_PAGE_SIZE,
  };
}
