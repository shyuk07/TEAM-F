import { useCallback, useEffect, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import { splitByTab } from '../domain/grouping';
import type { Reservation } from '../domain/reservation';
import { readErrorInfo } from './errorInfo';
import { fetchAllMine } from './fetchAllMine';
import { ReservationRepositoryToken } from './tokens';
import { useNow } from './useNow';

type LoadState =
  | { status: 'loading' }
  | { status: 'error'; errorCode: string; message: string }
  | { status: 'success'; active: Reservation[]; past: Reservation[] };

type RawState =
  | { status: 'loading' }
  | { status: 'error'; errorCode: string; message: string }
  | { status: 'success'; items: Reservation[] };

export type MyReservationsState = LoadState & { reload(): void };

// 원본 목록을 들고 있다가 렌더마다 현재 시각(useNow)으로 탭을 나눈다(pickup_end가 지나면 진행 중에서 빠짐).
export function useMyReservations(): MyReservationsState {
  const repo = useDep(ReservationRepositoryToken);
  const now = useNow();
  const [raw, setRaw] = useState<RawState>({ status: 'loading' });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchAllMine(repo, ctrl.signal).then(
      (items) => {
        if (!ctrl.signal.aborted) setRaw({ status: 'success', items });
      },
      (e: unknown) => {
        if (ctrl.signal.aborted) return;
        const info = readErrorInfo(e);
        setRaw({ status: 'error', errorCode: info.errorCode, message: info.message });
      },
    );
    return () => ctrl.abort();
  }, [repo, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  if (raw.status !== 'success') return { ...raw, reload };
  return { status: 'success', ...splitByTab(raw.items, now), reload };
}
