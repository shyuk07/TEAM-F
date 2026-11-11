import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ApiError } from '@/shared/api/error';
import { useStoreProducts } from '@/features/products/application/useStoreProducts';
import { FakeProductRepository } from '../../../entities/product/fakes/fakeProductRepository.fake';
import { breadProduct } from '../../../entities/product/fakes/products';
import { deferred } from '../../auth/fakes/deferred';
import { createProductsContainer } from '../fakes/renderProducts';

function setup(repo = new FakeProductRepository()) {
  const ctx = createProductsContainer({
    repo,
    commands: createProductsContainer().commands,
  });
  return { repo, wrapper: ctx.wrapper };
}

describe('features/products application useStoreProducts', () => {
  it('처음에는 loading이고 findByStore(storeId)가 불린다', async () => {
    const { repo, wrapper } = setup();
    const { result } = renderHook(() => useStoreProducts('s1'), { wrapper });
    expect(result.current.status).toBe('loading');
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(repo.findByStore.mock.calls[0][0]).toBe('s1');
  });

  it('목록으로 resolve되면 success와 data.items', async () => {
    const { repo, wrapper } = setup();
    const page = { items: [breadProduct], page: 1, size: 100, total: 1 };
    repo.findByStore.mockResolvedValue(page);
    const { result } = renderHook(() => useStoreProducts('s1'), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current.data?.items).toEqual([breadProduct]);
  });

  it('items: [], total: 0도 success다(빈 상태 판단은 화면)', async () => {
    const { repo, wrapper } = setup();
    repo.findByStore.mockResolvedValue({ items: [], page: 1, size: 100, total: 0 });
    const { result } = renderHook(() => useStoreProducts('s1'), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current.data?.total).toBe(0);
  });

  it('reject되면 error', async () => {
    const { repo, wrapper } = setup();
    repo.findByStore.mockRejectedValue(new ApiError(500, 'UNKNOWN', 'x'));
    const { result } = renderHook(() => useStoreProducts('s1'), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('error'));
  });

  it('reload()를 부르면 findByStore가 2번 불린다', async () => {
    const { repo, wrapper } = setup();
    const { result } = renderHook(() => useStoreProducts('s1'), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('success'));
    await act(async () => {
      result.current.reload();
    });
    await waitFor(() => expect(repo.findByStore).toHaveBeenCalledTimes(2));
  });

  it('언마운트하면 넘긴 signal이 abort되고 이후 resolve해도 상태가 바뀌지 않는다', async () => {
    const { repo, wrapper } = setup();
    const d = deferred<Awaited<ReturnType<FakeProductRepository['findByStore']>>>();
    repo.findByStore.mockReturnValue(d.promise);
    const { result, unmount } = renderHook(() => useStoreProducts('s1'), { wrapper });
    await waitFor(() => expect(repo.findByStore).toHaveBeenCalledTimes(1));
    const signal = repo.findByStore.mock.calls[0][1];
    expect(signal?.aborted).toBe(false);
    unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      d.resolve({ items: [breadProduct], page: 1, size: 100, total: 1 });
    });
    expect(result.current.status).toBe('loading');
  });
});
