import { useCallback, useEffect, useRef, useState } from 'react';
import type { Store } from '@/entities/store';
import { useMyStore } from '@/entities/store';
import { useDep } from '@/shared/lib/di';
import { readErrorInfo } from '@/shared/lib/errorInfo';
import { closeStoreErrorMessage } from '../domain/storeMessage';
import { closeStore } from './closeStore';
import { StoreCommandsToken } from './tokens';

// useOpenStore와 같은 구조. 성공하면 reload()(가드가 CLOSED를 보고 O0로 보냄, D-17).
export function useCloseStore(store: Store): {
  submit(typedName: string): Promise<void>;
  pending: boolean;
  errorMessage: string | null;
} {
  const commands = useDep(StoreCommandsToken);
  const { reload } = useMyStore();
  const [pending, setPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const busyRef = useRef(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const submit = useCallback(
    async (typedName: string): Promise<void> => {
      // 중복 제출 방지: 이미 진행 중이면 아무것도 하지 않는다(F10).
      if (busyRef.current) return;
      busyRef.current = true;
      setPending(true);
      setErrorMessage(null);
      const ctrl = new AbortController();
      try {
        await closeStore({ commands }, { store, typedName }, ctrl.signal);
        // 성공하면 상점 조회를 다시 불러 가드가 CLOSED를 보고 O0로 보낸다(D-17).
        if (mountedRef.current) reload();
      } catch (e) {
        const info = readErrorInfo(e);
        if (mountedRef.current) {
          setErrorMessage(closeStoreErrorMessage(info));
          if (info.errorCode === 'STORE_ALREADY_CLOSED') reload();
        }
        throw e;
      } finally {
        busyRef.current = false;
        // 언마운트 뒤에는 상태를 바꾸지 않는다.
        if (mountedRef.current) setPending(false);
      }
    },
    [commands, reload, store],
  );

  return { submit, pending, errorMessage };
}
