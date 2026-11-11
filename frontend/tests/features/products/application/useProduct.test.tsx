import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ApiError } from '@/shared/api/error';
import { useProduct } from '@/features/products/application/useProduct';
import { FakeProductRepository } from '../../../entities/product/fakes/fakeProductRepository.fake';
import { baguetteProduct, breadProduct } from '../../../entities/product/fakes/products';
import { deferred } from '../../auth/fakes/deferred';
import { createProductsContainer } from '../fakes/renderProducts';

function setup(repo = new FakeProductRepository()) {
  const { wrapper } = createProductsContainer({
    repo,
    commands: createProductsContainer().commands,
  });
  return { repo, wrapper };
}

describe('features/products application useProduct', () => {
  it('처음 loading → findById(productId) → success와 data', async () => {
    const { repo, wrapper } = setup();
    const { result } = renderHook(() => useProduct('p1'), { wrapper });
    expect(result.current.status).toBe('loading');
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(repo.findById.mock.calls[0][0]).toBe('p1');
    expect(result.current.data).toEqual(breadProduct);
  });

  it('reject되면 error이고 error에 ApiError가 담긴다', async () => {
    const { repo, wrapper } = setup();
    const err = new ApiError(404, 'NOT_FOUND', 'x');
    repo.findById.mockRejectedValue(err);
    const { result } = renderHook(() => useProduct('p1'), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.error).toBe(err);
  });

  // C1(D-35): failure = 구분 + 문구
  it('failure는 loading·success에서 null이다', async () => {
    const { wrapper } = setup();
    const { result } = renderHook(() => useProduct('p1'), { wrapper });
    expect(result.current.failure).toBeNull();
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current.failure).toBeNull();
  });

  it.each([
    [404, 'NOT_FOUND'],
    [403, 'FORBIDDEN'],
  ])('%i %s reject → failure = notFound + 「상품을 찾을 수 없어요.」', async (status, code) => {
    const { repo, wrapper } = setup();
    repo.findById.mockRejectedValue(new ApiError(status, code, 'x'));
    const { result } = renderHook(() => useProduct('p1'), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.failure).toEqual({
      kind: 'notFound',
      message: '상품을 찾을 수 없어요.',
    });
  });

  it('500 reject → failure = loadFailed + 불러오기 문구', async () => {
    const { repo, wrapper } = setup();
    repo.findById.mockRejectedValue(new ApiError(500, 'UNKNOWN', 'x'));
    const { result } = renderHook(() => useProduct('p1'), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.failure).toEqual({
      kind: 'loadFailed',
      message: '상품 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.',
    });
  });

  it('reload()로 호출이 2회가 된다', async () => {
    const { repo, wrapper } = setup();
    const { result } = renderHook(() => useProduct('p1'), { wrapper });
    await waitFor(() => expect(result.current.status).toBe('success'));
    await act(async () => {
      result.current.reload();
    });
    await waitFor(() => expect(repo.findById).toHaveBeenCalledTimes(2));
  });

  it('언마운트하면 signal이 abort되고 늦은 resolve로 상태가 바뀌지 않는다', async () => {
    const { repo, wrapper } = setup();
    const d = deferred<typeof breadProduct>();
    repo.findById.mockReturnValue(d.promise);
    const { result, unmount } = renderHook(() => useProduct('p1'), { wrapper });
    await waitFor(() => expect(repo.findById).toHaveBeenCalledTimes(1));
    const signal = repo.findById.mock.calls[0][1];
    unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      d.resolve(breadProduct);
    });
    expect(result.current.status).toBe('loading');
  });

  it('productId가 바뀌면 loading으로 돌아가 다시 호출한다', async () => {
    const { repo, wrapper } = setup();
    repo.findById.mockImplementation((id) =>
      Promise.resolve(id === 'p2' ? baguetteProduct : breadProduct),
    );
    const { result, rerender } = renderHook(({ id }) => useProduct(id), {
      wrapper,
      initialProps: { id: 'p1' },
    });
    await waitFor(() => expect(result.current.status).toBe('success'));
    rerender({ id: 'p2' });
    expect(result.current.status).toBe('loading');
    await waitFor(() => expect(result.current.data).toEqual(baguetteProduct));
    expect(repo.findById.mock.calls.map((c) => c[0])).toEqual(['p1', 'p2']);
  });
});
