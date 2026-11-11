import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ApiError } from '@/shared/api/error';
import { useCreateProduct } from '@/features/products/application/useCreateProduct';
import type { ProductFormValue } from '@/features/products/domain/productForm';
import { createdProduct } from '../../../entities/product/fakes/products';
import { deferred } from '../../auth/fakes/deferred';
import { FakeProductCommands } from '../fakes/fakeProductCommands.fake';
import { createProductsContainer } from '../fakes/renderProducts';

const value: ProductFormValue = {
  name: '식빵',
  originalPrice: 12000,
  category: null,
  description: null,
};

function setup(commands = new FakeProductCommands()) {
  const { wrapper } = createProductsContainer({
    repo: createProductsContainer().repo,
    commands,
  });
  return { commands, wrapper };
}

const TOO_LARGE = '사진이 5MB보다 커요. 더 작은 사진을 골라 주세요.';

describe('features/products application useCreateProduct', () => {
  it('처음에는 idle이고 오류가 없다', () => {
    const { wrapper } = setup();
    const { result } = renderHook(() => useCreateProduct(), { wrapper });
    expect(result.current.status).toBe('idle');
    expect(result.current.errorMessage).toBeNull();
    expect(result.current.photoError).toBe(false);
  });

  it('submit 중에는 submitting, 성공하면 Product를 resolve하고 idle', async () => {
    const commands = new FakeProductCommands();
    const d = deferred<typeof createdProduct>();
    commands.create.mockReturnValue(d.promise);
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useCreateProduct(), { wrapper });
    let promise!: Promise<unknown>;
    act(() => {
      promise = result.current.submit('s1', value, null);
    });
    await waitFor(() => expect(result.current.status).toBe('submitting'));
    await act(async () => {
      d.resolve(createdProduct);
      await expect(promise).resolves.toBe(createdProduct);
    });
    expect(result.current.status).toBe('idle');
  });

  it('STORE_SUSPENDED 실패: null을 resolve, status=error, 정지 문구, photoError false', async () => {
    const commands = new FakeProductCommands();
    commands.create.mockRejectedValue(new ApiError(400, 'STORE_SUSPENDED', 'x'));
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useCreateProduct(), { wrapper });
    await act(async () => {
      await expect(result.current.submit('s1', value, null)).resolves.toBeNull();
    });
    expect(result.current.status).toBe('error');
    expect(result.current.errorMessage).toBe('정지된 상점에서는 상품을 등록할 수 없어요.');
    expect(result.current.photoError).toBe(false);
  });

  it('IMAGE_TOO_LARGE: photoError true, errorMessage = 5MB 문구', async () => {
    const commands = new FakeProductCommands();
    commands.create.mockRejectedValue(new ApiError(400, 'IMAGE_TOO_LARGE', 'x'));
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useCreateProduct(), { wrapper });
    await act(async () => {
      await result.current.submit('s1', value, null);
    });
    expect(result.current.photoError).toBe(true);
    expect(result.current.errorMessage).toBe(TOO_LARGE);
  });

  it('UNSUPPORTED_IMAGE_TYPE도 photoError true', async () => {
    const commands = new FakeProductCommands();
    commands.create.mockRejectedValue(new ApiError(400, 'UNSUPPORTED_IMAGE_TYPE', 'x'));
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useCreateProduct(), { wrapper });
    await act(async () => {
      await result.current.submit('s1', value, null);
    });
    expect(result.current.photoError).toBe(true);
  });

  it('submitting 중 submit 재호출은 commands.create를 추가로 부르지 않는다', async () => {
    const commands = new FakeProductCommands();
    commands.create.mockReturnValue(new Promise(() => {}));
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useCreateProduct(), { wrapper });
    act(() => {
      void result.current.submit('s1', value, null);
    });
    await waitFor(() => expect(result.current.status).toBe('submitting'));
    act(() => {
      void result.current.submit('s1', value, null);
    });
    expect(commands.create).toHaveBeenCalledTimes(1);
  });

  // A3: 서버 message를 화면 문구로 쓰지 않는다
  it('VALIDATION_ERROR는 서버 message 대신 공통 저장 실패 문구를 errorMessage로 둔다', async () => {
    const commands = new FakeProductCommands();
    commands.create.mockRejectedValue(new ApiError(400, 'VALIDATION_ERROR', 'field required'));
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useCreateProduct(), { wrapper });
    await act(async () => {
      await result.current.submit('s1', value, null);
    });
    expect(result.current.errorMessage).toBe('저장하지 못했어요. 잠시 후 다시 시도해 주세요.');
    expect(result.current.errorMessage).not.toContain('field required');
  });

  it('실패 뒤 reset()하면 idle이고 errorMessage가 null', async () => {
    const commands = new FakeProductCommands();
    commands.create.mockRejectedValue(new ApiError(400, 'STORE_CLOSED', 'x'));
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useCreateProduct(), { wrapper });
    await act(async () => {
      await result.current.submit('s1', value, null);
    });
    expect(result.current.status).toBe('error');
    act(() => result.current.reset());
    expect(result.current.status).toBe('idle');
    expect(result.current.errorMessage).toBeNull();
  });

  it('언마운트하면 요청 signal이 abort된다', async () => {
    const commands = new FakeProductCommands();
    commands.create.mockReturnValue(new Promise(() => {}));
    const { wrapper } = setup(commands);
    const { result, unmount } = renderHook(() => useCreateProduct(), { wrapper });
    act(() => {
      void result.current.submit('s1', value, null);
    });
    await waitFor(() => expect(commands.create).toHaveBeenCalledTimes(1));
    const signal = commands.create.mock.calls[0][3];
    unmount();
    expect(signal?.aborted).toBe(true);
  });
});
