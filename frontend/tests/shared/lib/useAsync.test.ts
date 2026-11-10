import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useAsync } from '@/shared/lib/useAsync';

type Deferred<T> = { promise: Promise<T>; resolve(v: T): void; reject(e: unknown): void };

function deferred<T>(): Deferred<T> {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe('shared/lib/useAsync', () => {
  it('처음 상태는 loading이다', () => {
    const d = deferred<string>();
    const { result } = renderHook(() => useAsync(() => d.promise, 'k1'));
    expect(result.current.status).toBe('loading');
  });

  it('load가 resolve하면 success와 data가 된다', async () => {
    const d = deferred<string>();
    const { result } = renderHook(() => useAsync(() => d.promise, 'k1'));
    await act(async () => {
      d.resolve('값');
    });
    expect(result.current).toStrictEqual({ status: 'success', data: '값' });
  });

  it('load가 reject하면 error와 그 값이 된다', async () => {
    const d = deferred<string>();
    const err = new Error('실패');
    const { result } = renderHook(() => useAsync(() => d.promise, 'k1'));
    await act(async () => {
      d.reject(err);
    });
    expect(result.current.status).toBe('error');
    expect(result.current.error).toBe(err);
  });

  it('key가 바뀌면 loading으로 돌아간 뒤 다시 불러온다', async () => {
    let key = 'k1';
    const { result, rerender } = renderHook(() =>
      useAsync(() => Promise.resolve(`값-${key}`), key),
    );
    await waitFor(() => expect(result.current.status).toBe('success'));
    key = 'k2';
    rerender();
    expect(result.current.status).toBe('loading');
    await waitFor(() => expect(result.current).toStrictEqual({ status: 'success', data: '값-k2' }));
  });

  it('reload()를 부르면 다시 불러온다(호출 횟수 2)', async () => {
    const load = vi.fn(() => Promise.resolve('값'));
    const { result } = renderHook(() => useAsync(load, 'k1'));
    await waitFor(() => expect(result.current.status).toBe('success'));
    await act(async () => {
      result.current.reload();
    });
    expect(load).toHaveBeenCalledTimes(2);
  });

  it('언마운트하면 signal.aborted가 true이고 이후 resolve해도 상태가 바뀌지 않는다', async () => {
    const signals: AbortSignal[] = [];
    const d = deferred<string>();
    const { result, unmount } = renderHook(() =>
      useAsync((signal) => {
        signals.push(signal);
        return d.promise;
      }, 'k1'),
    );
    unmount();
    expect(signals[0].aborted).toBe(true);
    await act(async () => {
      d.resolve('늦은 값');
    });
    expect(result.current.status).toBe('loading');
  });

  it('key가 바뀌어 앞 요청이 늦게 끝나도 앞 결과로 상태를 바꾸지 않는다', async () => {
    const first = deferred<string>();
    const seen: string[] = [];
    const { result, rerender } = renderHook(() => {
      const key = seen.length === 0 ? 'k1' : 'k2';
      return useAsync(() => {
        const isSecond = seen.length > 0;
        seen.push(key);
        return isSecond ? Promise.resolve('두번째') : first.promise;
      }, key);
    });
    rerender();
    await waitFor(() =>
      expect(result.current).toStrictEqual({ status: 'success', data: '두번째' }),
    );
    await act(async () => {
      first.resolve('늦은 첫번째');
    });
    expect(result.current.status).toBe('success');
    expect(result.current.data).toBe('두번째');
  });
});
