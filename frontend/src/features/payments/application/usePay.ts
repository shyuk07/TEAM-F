import { useCallback, useEffect, useRef, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import type { Payment } from '../domain/payment';
import { readErrorInfo, type ErrorInfo } from './errorInfo';
import { PaymentRepositoryToken } from './tokens';

export type PayState = {
  pay(input: { reservationId: string; usePoint: number }): Promise<Payment | null>;
  pending: boolean;
  error: ErrorInfo | null;
};

// 실패해도 예약은 그대로라 다시 결제할 수 있다(REQ-32).
export function usePay(): PayState {
  const repo = useDep(PaymentRepositoryToken);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ErrorInfo | null>(null);
  const busy = useRef(false);
  const ctrl = useRef<AbortController | null>(null);

  useEffect(() => () => ctrl.current?.abort(), []);

  const pay = useCallback(
    async (input: { reservationId: string; usePoint: number }) => {
      if (busy.current) return null;
      busy.current = true;
      const c = new AbortController();
      ctrl.current = c;
      setPending(true);
      setError(null);
      try {
        return await repo.pay(input, c.signal);
      } catch (e) {
        if (!c.signal.aborted) setError(readErrorInfo(e));
        return null;
      } finally {
        busy.current = false;
        if (!c.signal.aborted) setPending(false);
      }
    },
    [repo],
  );

  return { pay, pending, error };
}
