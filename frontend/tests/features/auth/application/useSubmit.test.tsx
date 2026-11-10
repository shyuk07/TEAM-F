import { act, renderHook } from '@testing-library/react';
import { useSubmit } from '@/features/auth/application/useSubmit';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../fakes/deferred';

const initial = { pending: false, error: null, done: false };

function setup<R>(run: (x: string) => Promise<R>) {
  const spy = vi.fn(run);
  const hook = renderHook(() => useSubmit(spy));
  return { ...hook, run: spy };
}

describe('useSubmit', () => {
  it('처음 상태는 {pending:false, error:null, done:false}다', () => {
    const { result } = setup(() => Promise.resolve('ok'));
    expect(result.current.state).toEqual(initial);
  });

  it('submit 중에는 pending이고 성공하면 done이 되며 결과를 돌려준다', async () => {
    const d = deferred<string>();
    const { result, run } = setup(() => d.promise);
    let returned: Promise<string | undefined> | undefined;
    act(() => {
      returned = result.current.submit('a');
    });
    expect(result.current.state).toEqual({ pending: true, error: null, done: false });
    expect(run).toHaveBeenCalledWith('a', expect.any(AbortSignal));
    await act(async () => {
      d.resolve('결과');
    });
    await expect(returned).resolves.toBe('결과');
    expect(result.current.state).toEqual({ pending: false, error: null, done: true });
  });

  it('실패하면 error가 ErrorInfo이고 undefined를 돌려준다', async () => {
    const { result } = setup(() =>
      Promise.reject(new ApiError(409, 'EMAIL_DUPLICATED', '이미 가입된 이메일입니다.')),
    );
    let returned: string | undefined = 'x';
    await act(async () => {
      returned = await result.current.submit('a');
    });
    expect(returned).toBeUndefined();
    expect(result.current.state).toEqual({
      pending: false,
      done: false,
      error: { status: 409, errorCode: 'EMAIL_DUPLICATED', message: '이미 가입된 이메일입니다.' },
    });
  });

  it('pending 동안 두 번째 submit은 run을 부르지 않고 undefined를 돌려준다', async () => {
    const d = deferred<string>();
    const { result, run } = setup(() => d.promise);
    let second: Promise<string | undefined> | undefined;
    act(() => {
      void result.current.submit('a');
      second = result.current.submit('b');
    });
    await expect(second).resolves.toBeUndefined();
    expect(run).toHaveBeenCalledTimes(1);
    await act(async () => {
      d.resolve('결과');
    });
  });

  it('언마운트 뒤 resolve돼도 상태 갱신 경고가 없다', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const d = deferred<string>();
    let received: AbortSignal | undefined;
    const run = vi.fn((input: string, signal: AbortSignal) => {
      void input;
      received = signal;
      return d.promise;
    });
    const { result, unmount } = renderHook(() => useSubmit(run));
    act(() => {
      void result.current.submit('a');
    });
    expect(run).toHaveBeenCalledTimes(1);
    expect(received?.aborted).toBe(false);
    unmount();
    expect(received?.aborted).toBe(true);
    await act(async () => {
      d.resolve('결과');
    });
    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it('reset()은 처음 상태로 되돌린다', async () => {
    const { result } = setup(() => Promise.reject(new ApiError(400, 'VALIDATION_ERROR', 'x')));
    await act(async () => {
      await result.current.submit('a');
    });
    expect(result.current.state.error).not.toBeNull();
    act(() => result.current.reset());
    expect(result.current.state).toEqual(initial);
  });
});
