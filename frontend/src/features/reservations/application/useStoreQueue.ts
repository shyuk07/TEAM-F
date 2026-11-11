import { useCallback, useEffect, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import { queueCounts, splitQueue } from '../domain/pickupQueue';
import type { StoreReservation } from '../domain/storeReservation';
import { StoreReservationRepositoryToken } from './tokens';

export type StoreQueueStatus = 'loading' | 'success' | 'error';

export function useStoreQueue(storeId: string): {
  status: StoreQueueStatus;
  waiting: StoreReservation[];
  doneToday: StoreReservation[];
  counts: { waiting: number; done: number };
  reload: () => Promise<void>;
} {
  const repo = useDep(StoreReservationRepositoryToken);
  const [nonce, setNonce] = useState(0);
  const [result, setResult] = useState<{
    reqKey: string;
    status: StoreQueueStatus;
    waiting: StoreReservation[];
    doneToday: StoreReservation[];
  } | null>(null);

  const reqKey = `${storeId}\u0000${nonce}`;

  const reload = useCallback(async () => {
    setNonce((n) => n + 1);
  }, []);

  useEffect(() => {
    if (!storeId) return;

    const ctrl = new AbortController();

    Promise.all([
      repo.findByStore(storeId, 'RESERVED', 1, 100, ctrl.signal),
      repo.findByStore(storeId, 'PICKED_UP', 1, 100, ctrl.signal),
    ])
      .then(([reservedRes, pickedUpRes]) => {
        if (!ctrl.signal.aborted) {
          const allItems = [...reservedRes.items, ...pickedUpRes.items];
          const splitted = splitQueue(allItems, new Date());
          setResult({
            reqKey,
            status: 'success',
            waiting: splitted.waiting,
            doneToday: splitted.doneToday,
          });
        }
      })
      .catch(() => {
        if (!ctrl.signal.aborted) {
          setResult({ reqKey, status: 'error', waiting: [], doneToday: [] });
        }
      });

    const onFocus = () => {
      void reload();
    };
    window.addEventListener('focus', onFocus);

    return () => {
      ctrl.abort();
      window.removeEventListener('focus', onFocus);
    };
  }, [repo, storeId, reqKey, reload]);

  if (!storeId) {
    return {
      status: 'success',
      waiting: [],
      doneToday: [],
      counts: { waiting: 0, done: 0 },
      reload,
    };
  }

  const current = result !== null && result.reqKey === reqKey ? result : null;
  const status: StoreQueueStatus = current?.status ?? 'loading';
  const waiting = current?.waiting ?? [];
  const doneToday = current?.doneToday ?? [];
  const counts = queueCounts(waiting, doneToday);

  return {
    status,
    waiting,
    doneToday,
    counts,
    reload,
  };
}
