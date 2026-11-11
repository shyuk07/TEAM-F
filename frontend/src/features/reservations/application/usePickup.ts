import { useCallback, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import { readErrorInfo } from '@/shared/lib/errorInfo';
import { pickupErrorMessage } from '../domain/pickupMessages';
import type { StoreReservation } from '../domain/storeReservation';
import { completePickup } from './completePickup';
import { PickupGatewayToken } from './tokens';

export type PickupStatus = 'idle' | 'running' | 'error';

export function usePickup(onDone?: () => void): {
  submit: (code: string, targetReservation?: StoreReservation) => Promise<boolean>;
  status: PickupStatus;
  errorMessage: string | null;
  lastDone: { reservation: StoreReservation; doneAt: Date } | null;
  reset: () => void;
} {
  const gateway = useDep(PickupGatewayToken);
  const [status, setStatus] = useState<PickupStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastDone, setLastDone] = useState<{
    reservation: StoreReservation;
    doneAt: Date;
  } | null>(null);

  // FIXME: 픽업 제출이 연결되지 않았다. 코드를 입력해도 픽업 완료가 처리되지 않는다
  //   왜: 코드만으로 픽업하는 API가 없다 (owner-today.md B-2, Q-1)
  //   언제: 결정 후 (사용자: 픽업 제출 방식), 늦어도 배포 전
  const submit = useCallback(
    async (code: string, targetReservation?: StoreReservation): Promise<boolean> => {
      if (!targetReservation) {
        // 예약 ID 없이 코드만 전달된 경우, 백엔드 API 부재로 실행 불가
        setErrorMessage('선택된 예약이 없거나 백엔드 픽업 API가 필요해요.');
        setStatus('error');
        return false;
      }

      setStatus('running');
      setErrorMessage(null);
      try {
        const res = await completePickup(
          { gateway },
          {
            reservationId: targetReservation.id,
            code,
          },
        );
        setLastDone({
          reservation: targetReservation,
          doneAt: res.pickedUpAt,
        });
        setStatus('idle');
        onDone?.();
        return true;
      } catch (e) {
        const info = readErrorInfo(e);
        setErrorMessage(pickupErrorMessage(info));
        setStatus('error');
        return false;
      }
    },
    [gateway, onDone],
  );

  const reset = useCallback(() => {
    setStatus('idle');
    setErrorMessage(null);
  }, []);

  return {
    submit,
    status,
    errorMessage,
    lastDone,
    reset,
  };
}
