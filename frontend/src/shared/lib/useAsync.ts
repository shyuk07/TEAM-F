import { useCallback, useEffect, useRef, useState } from 'react';

// 서버 데이터 조회 공용 훅 (docs/design/frontend/stores.md §2.1, react-implementation §2)
export type AsyncState<T> =
  | { status: 'loading'; data?: undefined; error?: undefined }
  | { status: 'error'; data?: undefined; error: unknown }
  | { status: 'success'; data: T; error?: undefined };

const LOADING: AsyncState<never> = { status: 'loading' } as const;

// key가 바뀌거나 reload()를 부르면 다시 불러온다. 정리된 요청의 결과로는 상태를 바꾸지 않는다(F10).
export function useAsync<T>(
  load: (signal: AbortSignal) => Promise<T>,
  key: string,
): AsyncState<T> & { reload(): void } {
  const [nonce, setNonce] = useState(0);
  const [result, setResult] = useState<{ reqKey: string; state: AsyncState<T> } | null>(null);
  const loadRef = useRef(load);
  const reqKey = `${key}\u0000${nonce}`;

  useEffect(() => {
    loadRef.current = load;
  }, [load]);

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

  // reload는 콜백으로 안정되고(reload 안정성 요건), 테스트의 toStrictEqual이 AsyncState 본체만
  // 비교할 수 있도록 열거 불가 속성으로 붙인다(설계안 §2.1 반환 모양 유지).
  const ret = { ...state } as AsyncState<T> & { reload(): void };
  Object.defineProperty(ret, 'reload', { value: reload, enumerable: false });
  return ret;
}
