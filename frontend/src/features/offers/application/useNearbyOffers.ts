import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import type { NearbyOffer } from '../domain/offer';
import { queryKey, type NearbyOfferQuery } from '../domain/search';
import { initialNearbyListState, nearbyListReducer } from './nearbyListState';
import { OfferRepositoryToken } from './tokens';

export type NearbyOffersView = {
  status: 'loading' | 'error' | 'empty' | 'success';
  items: NearbyOffer[];
  total: number;
  hasMore: boolean;
  loadingMore: boolean;
  moreFailed: boolean;
  loadMore(): void;
  reload(): void;
};

export function useNearbyOffers(query: NearbyOfferQuery | null): NearbyOffersView {
  const offers = useDep(OfferRepositoryToken);
  const [state, dispatch] = useReducer(nearbyListReducer, initialNearbyListState);
  const [nonce, setNonce] = useState(0);
  const queryRef = useRef(query);
  const moreCtrlRef = useRef<AbortController | null>(null);
  const key = query === null ? null : queryKey(query);

  useEffect(() => {
    queryRef.current = query;
  });

  useEffect(() => {
    const listKey = key ?? '';
    dispatch({ type: 'queryChanged', key: listKey });
    const q = queryRef.current;
    if (key === null || q === null) return undefined;
    const ctrl = new AbortController();
    offers.findNearby({ ...q, page: 1 }, ctrl.signal).then(
      (page) => {
        if (!ctrl.signal.aborted) dispatch({ type: 'firstLoaded', key: listKey, page });
      },
      (error: unknown) => {
        if (!ctrl.signal.aborted) dispatch({ type: 'firstFailed', key: listKey, error });
      },
    );
    return () => {
      ctrl.abort();
      moreCtrlRef.current?.abort();
      moreCtrlRef.current = null;
    };
  }, [offers, key, nonce]);

  const loadMore = useCallback(() => {
    const q = queryRef.current;
    if (q === null || key === null) return;
    if (state.key !== key || state.status !== 'ready' || !state.hasMore || state.loadingMore)
      return;
    if (moreCtrlRef.current !== null) return; // 같은 렌더 안의 중복 호출 방지
    const ctrl = new AbortController();
    moreCtrlRef.current = ctrl;
    dispatch({ type: 'moreRequested' });
    offers.findNearby({ ...q, page: state.page + 1 }, ctrl.signal).then(
      (page) => {
        if (ctrl.signal.aborted) return;
        moreCtrlRef.current = null;
        dispatch({ type: 'moreLoaded', key, page });
      },
      (error: unknown) => {
        if (ctrl.signal.aborted) return;
        moreCtrlRef.current = null;
        dispatch({ type: 'moreFailed', key, error });
      },
    );
  }, [offers, key, state.key, state.status, state.hasMore, state.loadingMore, state.page]);

  const reload = useCallback(() => {
    dispatch({ type: 'reload' });
    setNonce((n) => n + 1);
  }, []);

  // 질의가 바뀐 렌더에서 effect가 dispatch하기 전까지 이전 질의의 결과를 그리지 않는다.
  const stale = state.key !== (key ?? '');
  const status: NearbyOffersView['status'] = stale
    ? 'loading'
    : state.status === 'ready'
      ? state.items.length === 0
        ? 'empty'
        : 'success'
      : state.status;

  return {
    status,
    items: stale ? [] : state.items,
    total: stale ? 0 : state.total,
    hasMore: !stale && state.hasMore,
    loadingMore: !stale && state.loadingMore,
    moreFailed: !stale && state.moreFailed,
    loadMore,
    reload,
  };
}
