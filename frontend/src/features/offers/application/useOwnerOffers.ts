import { useCallback, useEffect, useRef, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import type { Offer } from '../domain/offer';
import { countByFilter, type OwnerFilter } from '../domain/ownerOffer';
import { OfferRepositoryToken } from './tokens';

export type OwnerOffersStatus = 'loading' | 'success' | 'error';

export function useOwnerOffers(storeId: string): {
  status: OwnerOffersStatus;
  openOffers: Offer[];
  closedOffers: Offer[];
  counts: { onSale: number; scheduled: number; soldOut: number };
  filter: OwnerFilter;
  setFilter: (f: OwnerFilter) => void;
  loadClosed: () => Promise<void>;
  reload: () => Promise<void>;
} {
  const repo = useDep(OfferRepositoryToken);
  const [nonce, setNonce] = useState(0);
  const [filter, setFilterState] = useState<OwnerFilter>('ON_SALE');
  const [result, setResult] = useState<{
    reqKey: string;
    status: OwnerOffersStatus;
    openOffers: Offer[];
    closedOffers: Offer[];
  } | null>(null);

  const closedLoadedRef = useRef(false);
  const reqKey = `${storeId}\u0000${nonce}`;

  useEffect(() => {
    if (!storeId) return;

    const ctrl = new AbortController();
    closedLoadedRef.current = false;

    repo
      .findByStore(storeId, ['SCHEDULED', 'ON_SALE', 'SOLD_OUT', 'SUSPENDED'], 1, 100, ctrl.signal)
      .then((res) => {
        if (!ctrl.signal.aborted) {
          setResult({
            reqKey,
            status: 'success',
            openOffers: res.items,
            closedOffers: [],
          });
        }
      })
      .catch(() => {
        if (!ctrl.signal.aborted) {
          setResult({ reqKey, status: 'error', openOffers: [], closedOffers: [] });
        }
      });

    return () => {
      ctrl.abort();
    };
  }, [repo, storeId, reqKey]);

  const loadClosed = useCallback(async () => {
    if (!storeId || closedLoadedRef.current) return;
    try {
      const res = await repo.findByStore(storeId, ['CLOSED'], 1, 100);
      closedLoadedRef.current = true;
      setResult((prev) =>
        prev
          ? {
              ...prev,
              closedOffers: res.items,
            }
          : null,
      );
    } catch {
      // 닫힌 할인 로드 실패는 유지
    }
  }, [repo, storeId]);

  const setFilter = useCallback(
    (nextFilter: OwnerFilter) => {
      setFilterState(nextFilter);
      if (nextFilter === 'CLOSED' && !closedLoadedRef.current) {
        void loadClosed();
      }
    },
    [loadClosed],
  );

  const reload = useCallback(async () => {
    setNonce((n) => n + 1);
  }, []);

  if (!storeId) {
    return {
      status: 'success',
      openOffers: [],
      closedOffers: [],
      counts: { onSale: 0, scheduled: 0, soldOut: 0 },
      filter,
      setFilter,
      loadClosed,
      reload,
    };
  }

  const current = result !== null && result.reqKey === reqKey ? result : null;
  const status: OwnerOffersStatus = current?.status ?? 'loading';
  const openOffers = current?.openOffers ?? [];
  const closedOffers = current?.closedOffers ?? [];
  const counts = countByFilter(openOffers);

  return {
    status,
    openOffers,
    closedOffers,
    counts,
    filter,
    setFilter,
    loadClosed,
    reload,
  };
}
