import { useCallback, useEffect, useRef, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import { readErrorInfo, type ErrorInfo } from './errorInfo';
import { ReservationRepositoryToken } from './tokens';

type ErrorView = { errorCode: string; message: string };

export type CancelReservationState = {
  cancel(id: string, onFailure?: (error: ErrorInfo) => void): Promise<boolean>;
  pending: boolean;
  error: ErrorView | null;
};

export function useCancelReservation(): CancelReservationState {
  const repo = useDep(ReservationRepositoryToken);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ErrorView | null>(null);
  const busy = useRef(false);
  const ctrl = useRef<AbortController | null>(null);

  useEffect(() => () => ctrl.current?.abort(), []);

  const cancel = useCallback(
    async (id: string, onFailure?: (error: ErrorInfo) => void) => {
      if (busy.current) return false;
      busy.current = true;
      const c = new AbortController();
      ctrl.current = c;
      setPending(true);
      setError(null);
      try {
        await repo.cancel(id, c.signal);
        return true;
      } catch (e) {
        if (!c.signal.aborted) {
          const info = readErrorInfo(e);
          setError({ errorCode: info.errorCode, message: info.message });
          onFailure?.(info);
        }
        return false;
      } finally {
        busy.current = false;
        if (!c.signal.aborted) setPending(false);
      }
    },
    [repo],
  );

  return { cancel, pending, error };
}
