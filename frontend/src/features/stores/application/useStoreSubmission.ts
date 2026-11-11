import { useCallback, useEffect, useRef, useState } from 'react';
import type { ErrorInfo } from '@/shared/lib/errorInfo';
import { readErrorInfo } from '@/shared/lib/errorInfo';
import { useMyStore } from '@/entities/store';

type UseStoreSubmissionOptions = {
  // 도메인 검증과 포트 호출을 함께 수행하는 application 유스케이스(D-19).
  // 개설처럼 성공해도 돌려주는 값이 있을 수 있지만, 이 공용 훅은 버린다(D-17: 화면 재조회로 갱신).
  run(arg: string, signal: AbortSignal): Promise<unknown>;
  // 던진 오류를 화면 문구로 바꾼다(F11).
  errorMessage(info: ErrorInfo): string;
  // 이 errorCode면 서버에 이미 반영된 상태라 조회를 다시 불러 화면 갱신을 맡긴다(D-17).
  conflictReload: string;
};

// useOpenStore·useCloseStore가 공유하는 제출 흐름: 중복 제출 방지(F10), pending·errorMessage 상태,
// 언마운트 뒤 상태 변경 금지, 성공·충돌 시 상점 조회를 다시 불러 화면 이동을 맡긴다(D-17).
export function useStoreSubmission(options: UseStoreSubmissionOptions): {
  submit(arg: string): Promise<void>;
  pending: boolean;
  errorMessage: string | null;
} {
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
    async (arg: string): Promise<void> => {
      // 중복 제출 방지: 이미 진행 중이면 아무것도 하지 않는다(F10).
      if (busyRef.current) return;
      busyRef.current = true;
      setPending(true);
      setErrorMessage(null);
      const ctrl = new AbortController();
      try {
        await options.run(arg, ctrl.signal);
        // 성공하면 상점 조회를 다시 불러 가드가 다음 화면으로 보낸다(D-17).
        if (mountedRef.current) reload();
      } catch (e) {
        const info = readErrorInfo(e);
        if (mountedRef.current) {
          setErrorMessage(options.errorMessage(info));
          if (info.errorCode === options.conflictReload) reload();
        }
        throw e;
      } finally {
        busyRef.current = false;
        // 언마운트 뒤에는 상태를 바꾸지 않는다.
        if (mountedRef.current) setPending(false);
      }
    },
    [options, reload],
  );

  return { submit, pending, errorMessage };
}
