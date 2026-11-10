import { useCallback, useEffect, useRef, useState } from 'react';

export type AsyncState<T> =
  | { status: 'loading'; data?: undefined; error?: undefined }
  | { status: 'error'; data?: undefined; error: unknown }
  | { status: 'success'; data: T; error?: undefined };

const LOADING = { status: 'loading' } as const;

// key가 바뀌거나 reload()를 부르면 다시 불러온다. 정리된 요청의 결과로는 상태를 바꾸지 않는다(F10).
// 결과는 어느 요청(reqKey)의 것인지와 함께 두고, 지금 요청의 결과가 아니면 로딩으로 본다.
// (effect 안에서 곧바로 setState하지 않는다: react-hooks/set-state-in-effect)
export function useAsync<T>(load: (signal: AbortSignal) => Promise<T>, key: string) {
  const [nonce, setNonce] = useState(0);
  const [result, setResult] = useState<{ reqKey: string; state: AsyncState<T> } | null>(null);
  const loadRef = useRef(load);
  const reqKey = `${key}\u0000${nonce}`;

  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    const ctrl = new AbortController();
    loadRef.current(ctrl.signal).then(
      (data) => {
        if (!ctrl.signal.aborted) setResult({ reqKey, state: { status: 'success', data } });
      },
      (error: unknown) => {
        if (!ctrl.signal.aborted) setResult({ reqKey, state: { status: 'error', error } });
      },
    );
    return () => ctrl.abort();
  }, [reqKey]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const state: AsyncState<T> = result !== null && result.reqKey === reqKey ? result.state : LOADING;
  return { ...state, reload };
}
