import { useEffect, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import type { Reservation } from '../domain/reservation';
import { readErrorInfo } from './errorInfo';
import { ReservationRepositoryToken } from './tokens';

export type MyReservationState =
  | { status: 'loading' }
  | { status: 'notFound' }
  | { status: 'error'; errorCode: string; message: string }
  | { status: 'success'; reservation: Reservation };

// 단건 조회(repo.get, GET /v1/reservations/{id})를 쓴다. 403·404 → notFound.
export function useMyReservation(id: string): MyReservationState {
  const repo = useDep(ReservationRepositoryToken);
  // 결과를 조회한 id와 함께 둬서, id가 바뀌면 effect 안 setState 없이 loading으로 보인다.
  const [result, setResult] = useState<{ id: string; state: MyReservationState } | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    const settle = (state: MyReservationState) => {
      if (!ctrl.signal.aborted) setResult({ id, state });
    };
    repo.get(id, ctrl.signal).then(
      (reservation) => settle({ status: 'success', reservation }),
      (e: unknown) => {
        const info = readErrorInfo(e);
        settle(
          info.status === 403 || info.status === 404
            ? { status: 'notFound' }
            : { status: 'error', errorCode: info.errorCode, message: info.message },
        );
      },
    );
    return () => ctrl.abort();
  }, [repo, id]);

  return result !== null && result.id === id ? result.state : { status: 'loading' };
}
