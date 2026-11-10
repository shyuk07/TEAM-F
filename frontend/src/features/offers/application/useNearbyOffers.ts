import { useEffect, useRef, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import { toNearbyQuery, type HomeFilter } from '../domain/homeFilter';
import type { GeoPoint } from '../domain/nearbyQuery';
import type { NearbyOffer } from '../domain/offer';
import { OfferRepositoryToken } from './tokens';

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

// 받은 결과는 어느 요청(key)의 것인지와 함께 둔다. key가 지금 요청과 다르면 loading으로 본다.
type Loaded = {
  key: string;
  status: 'success' | 'empty' | 'error';
  items: NearbyOffer[];
  total: number;
  page: number;
  loadingMore: boolean;
  loadMoreFailed: boolean;
};

function toPoint(lat: number | null, lng: number | null): GeoPoint | null {
  return lat !== null && lng !== null ? { lat, lng } : null;
}

// 같은 id가 다음 페이지에 다시 오면(목록 변동) 뒤에 온 것을 버린다(customer-home.md §3.2).
function appendUnique(items: NearbyOffer[], next: NearbyOffer[]): NearbyOffer[] {
  const seen = new Set(items.map((i) => i.offer.id));
  return [...items, ...next.filter((i) => !seen.has(i.offer.id))];
}

export function useNearbyOffers(
  filter: HomeFilter,
  location: GeoPoint | null,
  ready: boolean,
): NearbyOffersState {
  const repo = useDep(OfferRepositoryToken);
  const { sort, radiusKm, keyword } = filter;
  const lat = location?.lat ?? null;
  const lng = location?.lng ?? null;
  // retry()가 바꾸면 같은 조건으로 첫 페이지를 다시 받는다.
  const [attempt, setAttempt] = useState(0);
  // 요청 세대: ready가 false → true가 될 때(위치 재요청 포함)마다 올린다. 좌표가 같아도 앞 결과를 쓰지 않는다(customer-home.md D-33).
  const [generation, setGeneration] = useState(0);
  const [prevReady, setPrevReady] = useState(ready);
  if (prevReady !== ready) {
    setPrevReady(ready);
    if (ready) setGeneration((n) => n + 1);
  }
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const ctrlRef = useRef<AbortController | null>(null);
  const loadingMoreRef = useRef(false);
  const key = JSON.stringify([sort, radiusKm, keyword, lat, lng, attempt, generation]);

  useEffect(() => {
    if (!ready) return;
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    loadingMoreRef.current = false;
    const query = toNearbyQuery({ sort, radiusKm, keyword }, toPoint(lat, lng), 1);
    repo.findNearby(query, ctrl.signal).then(
      (page) => {
        if (ctrl.signal.aborted) return;
        setLoaded({
          key,
          status: page.items.length === 0 ? 'empty' : 'success',
          items: page.items,
          total: page.total,
          page: 1,
          loadingMore: false,
          loadMoreFailed: false,
        });
      },
      () => {
        // abort로 생긴 오류는 무시한다(F10).
        if (ctrl.signal.aborted) return;
        setLoaded({
          key,
          status: 'error',
          items: [],
          total: 0,
          page: 1,
          loadingMore: false,
          loadMoreFailed: false,
        });
      },
    );
    return () => ctrl.abort();
  }, [repo, ready, key, sort, radiusKm, keyword, lat, lng]);

  const current = ready && loaded !== null && loaded.key === key ? loaded : null;
  const hasMore = current?.status === 'success' && current.items.length < current.total;

  const loadMore = () => {
    const ctrl = ctrlRef.current;
    if (current === null || !hasMore || loadingMoreRef.current || ctrl === null) return;
    loadingMoreRef.current = true;
    const nextPage = current.page + 1;
    setLoaded({ ...current, loadingMore: true, loadMoreFailed: false });
    const settle = (update: (prev: Loaded) => Loaded) => {
      if (ctrl.signal.aborted) return;
      loadingMoreRef.current = false;
      setLoaded((prev) => (prev !== null && prev.key === key ? update(prev) : prev));
    };
    repo.findNearby(toNearbyQuery(filter, location, nextPage), ctrl.signal).then(
      (page) =>
        settle((prev) => ({
          ...prev,
          items: appendUnique(prev.items, page.items),
          total: page.total,
          page: nextPage,
          loadingMore: false,
        })),
      // 실패하면 목록은 그대로 두고 loadMoreFailed만 켠다.
      () => settle((prev) => ({ ...prev, loadingMore: false, loadMoreFailed: true })),
    );
  };

  const retry = () => setAttempt((n) => n + 1);

  return {
    status: current?.status ?? 'loading',
    items: current?.items ?? [],
    total: current?.total ?? 0,
    hasMore,
    loadingMore: current?.loadingMore ?? false,
    loadMoreFailed: current?.loadMoreFailed ?? false,
    loadMore,
    retry,
  };
}
