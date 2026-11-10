import { useState } from 'react';
import { useNow } from '@/shared/lib/useNow';
import { isValidRadiusKm } from '../domain/locationSheet';
import { emptyView, type EmptyView } from '../domain/offerEmpty';
import {
  DEFAULT_RADIUS_KM,
  DEFAULT_SORT,
  PAGE_SIZE,
  WIDEN_RADIUS_KM,
  isSortSelectable,
  locationChipLabel,
  normalizeKeyword,
  resolveSort,
  type LocationStatus,
  type NearbyOfferQuery,
  type OfferSortKey,
} from '../domain/search';
import { useCurrentLocation } from './useCurrentLocation';
import { useNearbyOffers, type NearbyOffersView } from './useNearbyOffers';

export type HomeOffers = {
  now: Date;
  location: { status: LocationStatus; hasLocation: boolean; retry(): void };
  radiusKm: number;
  setRadiusKm(km: number): void;
  sort: OfferSortKey;
  hasLocation: boolean;
  selectSort(key: OfferSortKey): void;
  keyword: string | undefined;
  submitKeyword(raw: string): void;
  chipLabel: string;
  list: NearbyOffersView;
  empty: EmptyView;
  runEmptyAction(): void;
};

export function useHomeOffers(): HomeOffers {
  const now = useNow(30_000);
  const location = useCurrentLocation();
  const [radiusKm, setRadiusKmState] = useState(DEFAULT_RADIUS_KM);
  const [selectedSort, setSelectedSort] = useState<OfferSortKey>(DEFAULT_SORT);
  const [keyword, setKeyword] = useState<string | undefined>(undefined);

  const hasLocation = location.status === 'located' && location.point !== null;
  const sort = resolveSort(selectedSort, hasLocation);

  // TODO: 목록에 품절 카드가 나오지 않는다(status 기본 ON_SALE만 조회).
  //   왜: 서버 status가 값 하나라 판매 중과 품절을 한 번에 못 받는다 (docs/design/frontend/offers.md C-2, D-12)
  //   언제: 결정 후 (사용자: 품절 카드 표시 방법)
  const query: NearbyOfferQuery | null =
    location.status === 'locating'
      ? null
      : {
          area:
            location.point !== null && location.status === 'located'
              ? { point: location.point, radiusKm }
              : null,
          keyword,
          sort,
          page: 1,
          size: PAGE_SIZE,
        };
  const list = useNearbyOffers(query);
  const empty = emptyView({ keyword, hasLocation, radiusKm });

  return {
    now,
    location: { status: location.status, hasLocation, retry: location.retry },
    radiusKm,
    setRadiusKm(km) {
      if (isValidRadiusKm(km)) setRadiusKmState(km);
    },
    sort,
    hasLocation,
    selectSort(key) {
      if (isSortSelectable(key, hasLocation)) setSelectedSort(key);
    },
    keyword,
    submitKeyword(raw) {
      setKeyword(normalizeKeyword(raw));
    },
    chipLabel: locationChipLabel(location.status, radiusKm),
    list,
    empty,
    runEmptyAction() {
      if (empty.action === 'clearKeyword') setKeyword(undefined);
      else if (empty.action === 'widenRadius') setRadiusKmState(WIDEN_RADIUS_KM);
    },
  };
}
