import { useCallback, useEffect, useRef, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import { readErrorInfo } from './errorInfo';
import { reserveOffer } from './reserveOffer';
import { ReservationRepositoryToken } from './tokens';

type ErrorView = { errorCode: string; message: string };

export type ReserveOfferState = {
  submit(quantity: number): Promise<void>;
  pending: boolean;
  error: ErrorView | null;
  pendingReservationId: string | null;
  createdReservationId: string | null;
};

export function useReserveOffer(offerId: string): ReserveOfferState {
  const repo = useDep(ReservationRepositoryToken);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ErrorView | null>(null);
  const [pendingReservationId, setPendingId] = useState<string | null>(null);
  const [createdReservationId, setCreatedId] = useState<string | null>(null);
  const busy = useRef(false);
  const ctrl = useRef<AbortController | null>(null);

  useEffect(() => () => ctrl.current?.abort(), []);

  const submit = useCallback(
    async (quantity: number) => {
      if (busy.current) return;
      busy.current = true;
      const c = new AbortController();
      ctrl.current = c;
      setPending(true);
      setError(null);
      try {
        const result = await reserveOffer(repo, { offerId, quantity }, c.signal);
        if (c.signal.aborted) return;
        if (result.kind === 'created') {
          setCreatedId(result.reservationId);
        } else {
          setPendingId(result.reservationId);
          setError({ errorCode: 'PENDING_RESERVATION_EXISTS', message: '' });
        }
      } catch (e) {
        if (c.signal.aborted) return;
        const info = readErrorInfo(e);
        setError({ errorCode: info.errorCode, message: info.message });
      } finally {
        busy.current = false;
        if (!c.signal.aborted) setPending(false);
      }
    },
    [repo, offerId],
  );

  return { submit, pending, error, pendingReservationId, createdReservationId };
}
