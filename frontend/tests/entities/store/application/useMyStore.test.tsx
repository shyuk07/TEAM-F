import type { ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
  MyStoreProvider,
  StoreRepositoryToken,
  useMyStore,
  useOwnerStore,
  type StoreRepository,
} from '@/entities/store';
import {
  MyStoreContext,
  type MyStoreContextValue,
} from '@/entities/store/application/myStoreContext';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { bind, Container } from '@/shared/lib/di';
import { ApiError } from '@/shared/api/error';
import { activeStore } from '../fakes/stores';
import { FakeStoreRepository } from '../fakes/fakeStoreRepository.fake';

function wrapperWith(fakes = new FakeStoreRepository()) {
  const container = new Container([bind(StoreRepositoryToken, fakes)]);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={container}>
      <MyStoreProvider>{children}</MyStoreProvider>
    </DepsProvider>
  );
  return { wrapper, fakes };
}

describe('entities/store useMyStoreController · MyStoreProvider', () => {
  it('findMine이 pending이면 lookup은 loading이다', async () => {
    const fakes = new FakeStoreRepository();
    fakes.findMine.mockReturnValue(new Promise(() => {}));
    const { wrapper } = wrapperWith(fakes);
    const { result } = renderHook(() => useMyStore(), { wrapper });
    expect(result.current.lookup.status).toBe('loading');
  });

  it('store를 돌려주면 found가 된다', async () => {
    const { wrapper } = wrapperWith();
    const { result } = renderHook(() => useMyStore(), { wrapper });
    await waitFor(() =>
      expect(result.current.lookup).toStrictEqual({ status: 'found', store: activeStore }),
    );
  });

  it('null을 돌려주면 none이 된다', async () => {
    const fakes = new FakeStoreRepository();
    fakes.findMine.mockResolvedValue(null);
    const { wrapper } = wrapperWith(fakes);
    const { result } = renderHook(() => useMyStore(), { wrapper });
    await waitFor(() => expect(result.current.lookup.status).toBe('none'));
  });

  it('NETWORK_ERROR를 던지면 error lookup이 된다', async () => {
    const fakes = new FakeStoreRepository();
    fakes.findMine.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', '끊김'));
    const { wrapper } = wrapperWith(fakes);
    const { result } = renderHook(() => useMyStore(), { wrapper });
    await waitFor(() =>
      expect(result.current.lookup).toEqual({
        status: 'error',
        errorCode: 'NETWORK_ERROR',
        message: '끊김',
      }),
    );
  });

  it('reload()를 부르면 loading으로 갔다가 다시 found이고 findMine이 2번 불린다', async () => {
    const { wrapper, fakes } = wrapperWith();
    const { result } = renderHook(() => useMyStore(), { wrapper });
    await waitFor(() => expect(result.current.lookup.status).toBe('found'));
    await act(async () => {
      result.current.reload();
    });
    await waitFor(() => expect(result.current.lookup.status).toBe('found'));
    expect(fakes.findMine).toHaveBeenCalledTimes(2);
  });

  it('언마운트하면 넘긴 signal이 abort된다', async () => {
    const signals: AbortSignal[] = [];
    const fakes = new FakeStoreRepository();
    fakes.findMine.mockImplementation((signal?: AbortSignal) => {
      if (signal) signals.push(signal);
      return Promise.resolve(activeStore);
    });
    const { wrapper } = wrapperWith(fakes);
    const { unmount } = renderHook(() => useMyStore(), { wrapper });
    await waitFor(() => expect(signals.length).toBeGreaterThan(0));
    unmount();
    expect(signals.every((s) => s.aborted)).toBe(true);
  });

  it('MyStoreProvider 밖에서 useMyStore()를 호출하면 Error를 던진다', () => {
    expect(() => renderHook(() => useMyStore()).result.current).toThrow(
      'MyStoreProvider 밖에서 useMyStore를 호출했습니다.',
    );
  });

  // 렌더 중 던진 Error는 RTL renderHook 호출문에서 동기적으로 다시 던져진다. 비동기 컨트롤러가 섞이면 에러가
  // 단언 밖에서 탈출하므로 none lookup을 동기 Context로 고정해 첫 렌더에서 던지는지 확인한다(D-결정 2026-11-10).
  it('lookup이 none일 때 useOwnerStore()는 Error를 던진다', () => {
    const value: MyStoreContextValue = {
      lookup: { status: 'none' },
      reload: () => undefined,
    };
    const wrapper = ({ children }: { children: ReactNode }) => (
      <MyStoreContext.Provider value={value}>{children}</MyStoreContext.Provider>
    );
    expect(() => renderHook(() => useOwnerStore(), { wrapper })).toThrow(
      '상점이 없는 상태에서 useOwnerStore를 호출했습니다.',
    );
  });

  it('found일 때 useOwnerStore()는 Store를 돌려준다', async () => {
    const { wrapper } = wrapperWith();
    const { result } = renderHook(() => useOwnerStore(), { wrapper });
    await waitFor(() => expect(result.current).toStrictEqual(activeStore));
  });
});

describe('MyStoreContext 포트 바인딩 모양', () => {
  it('StoreRepositoryToken으로 가짜 구현체를 풀 수 있다', () => {
    const container = new Container([bind(StoreRepositoryToken, new FakeStoreRepository())]);
    const repo = container.get<StoreRepository>(StoreRepositoryToken);
    expect(vi.mocked(repo.findMine)).toBeTypeOf('function');
  });
});
