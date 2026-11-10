import { useCallback, useEffect, useRef, useState } from 'react';
import { readErrorInfo, type ErrorInfo } from './errorInfo';

// 내부 파일(공개 API 아님): 4개 폼 훅의 공통 제출 상태 전이
export type SubmitState = { pending: boolean; error: ErrorInfo | null; done: boolean };

const INITIAL: SubmitState = { pending: false, error: null, done: false };

// run은 마운트 동안 유지되는 signal을 받는다. 언마운트하면 abort하고, 그 뒤에는 상태를 바꾸지 않는다(auth-account.md D-32).
export function useSubmit<I, R>(
  run: (input: I, signal: AbortSignal) => Promise<R>,
): { state: SubmitState; submit(input: I): Promise<R | undefined>; reset(): void } {
  const [state, setState] = useState<SubmitState>(INITIAL);
  const runRef = useRef(run);
  const pendingRef = useRef(false);
  const ctrlRef = useRef<AbortController | null>(null);

  useEffect(() => {
    runRef.current = run;
  });

  useEffect(() => {
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    return () => ctrl.abort();
  }, []);

  const submit = useCallback(async (input: I): Promise<R | undefined> => {
    if (pendingRef.current) return undefined;
    const ctrl = ctrlRef.current ?? new AbortController();
    ctrlRef.current = ctrl;
    const { signal } = ctrl;
    pendingRef.current = true;
    setState({ pending: true, error: null, done: false });
    try {
      const result = await runRef.current(input, signal);
      if (signal.aborted) return undefined;
      setState({ pending: false, error: null, done: true });
      return result;
    } catch (e) {
      // abort로 생긴 오류와 언마운트 뒤 오류는 상태로 만들지 않는다.
      if (!signal.aborted) setState({ pending: false, error: readErrorInfo(e), done: false });
      return undefined;
    } finally {
      pendingRef.current = false;
    }
  }, []);

  const reset = useCallback(() => setState(INITIAL), []);

  return { state, submit, reset };
}
