import { useCallback, useEffect, useRef, useState } from 'react';
import { readErrorInfo, type ErrorInfo } from '@/shared/lib/errorInfo';

export type RunStatus = 'idle' | 'running' | 'error';

type RunOptions = {
  // 던진 오류를 화면 문구로 바꾼다.
  message(info: ErrorInfo): string;
};

// create·save·toggle 훅이 공유하는 제출 흐름: 중복 제출 방지, 언마운트 abort(F10).
export function useProductRun(): {
  run<T>(task: (signal: AbortSignal) => Promise<T>, options: RunOptions): Promise<T | null>;
  status: RunStatus;
  errorMessage: string | null;
  errorCode: string | null;
  reset(): void;
} {
  const [status, setStatus] = useState<RunStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const ctrlRef = useRef<AbortController | null>(null);

  useEffect(
    () => () => {
      ctrlRef.current?.abort();
    },
    [],
  );

  const run = useCallback(
    async <T>(
      task: (signal: AbortSignal) => Promise<T>,
      options: RunOptions,
    ): Promise<T | null> => {
      if (ctrlRef.current) return null; // 진행 중이면 무시
      const ctrl = new AbortController();
      ctrlRef.current = ctrl;
      setStatus('running');
      setErrorMessage(null);
      setErrorCode(null);
      try {
        const result = await task(ctrl.signal);
        if (ctrl.signal.aborted) return null;
        setStatus('idle');
        return result;
      } catch (e) {
        if (ctrl.signal.aborted) return null;
        const info = readErrorInfo(e);
        setStatus('error');
        setErrorMessage(options.message(info));
        setErrorCode(info.errorCode);
        return null;
      } finally {
        if (ctrlRef.current === ctrl) ctrlRef.current = null;
      }
    },
    [],
  );

  const reset = useCallback(() => {
    setStatus((s) => (s === 'running' ? s : 'idle'));
    setErrorMessage(null);
    setErrorCode(null);
  }, []);

  return { run, status, errorMessage, errorCode, reset };
}
