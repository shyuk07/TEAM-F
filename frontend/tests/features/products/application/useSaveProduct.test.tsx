import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ApiError } from '@/shared/api/error';
import { useSaveProduct } from '@/features/products/application/useSaveProduct';
import { breadProduct } from '../../../entities/product/fakes/products';
import { FakeProductCommands } from '../fakes/fakeProductCommands.fake';
import { createProductsContainer } from '../fakes/renderProducts';

function setup(commands = new FakeProductCommands()) {
  const { wrapper } = createProductsContainer({
    repo: createProductsContainer().repo,
    commands,
  });
  return { commands, wrapper };
}

describe('features/products application useSaveProduct', () => {
  it('성공하면 갱신된 Product를 resolve하고 idle', async () => {
    const commands = new FakeProductCommands();
    const updated = { ...breadProduct, name: '새 이름' };
    commands.update.mockResolvedValue(updated);
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useSaveProduct(), { wrapper });
    await act(async () => {
      await expect(result.current.submit(breadProduct, { name: '새 이름' })).resolves.toBe(updated);
    });
    expect(result.current.status).toBe('idle');
    expect(commands.update.mock.calls[0].slice(0, 2)).toEqual(['p1', { name: '새 이름' }]);
  });

  // A3: 서버 message를 쓰지 않고 공통 문구
  it('VALIDATION_ERROR 400이면 서버 message를 쓰지 않고 공통 문구가 errorMessage가 된다', async () => {
    const commands = new FakeProductCommands();
    commands.update.mockRejectedValue(
      new ApiError(400, 'VALIDATION_ERROR', '정상 가격은 진행 중인 할인 가격보다 커야 합니다.'),
    );
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useSaveProduct(), { wrapper });
    await act(async () => {
      await expect(result.current.submit(breadProduct, { originalPrice: 1 })).resolves.toBeNull();
    });
    expect(result.current.status).toBe('error');
    expect(result.current.errorMessage).toBe('저장하지 못했어요. 잠시 후 다시 시도해 주세요.');
  });

  it('submitting 중 재제출은 무시된다', async () => {
    const commands = new FakeProductCommands();
    commands.update.mockReturnValue(new Promise(() => {}));
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useSaveProduct(), { wrapper });
    act(() => {
      void result.current.submit(breadProduct, { name: 'a' });
    });
    await waitFor(() => expect(result.current.status).toBe('submitting'));
    act(() => {
      void result.current.submit(breadProduct, { name: 'b' });
    });
    expect(commands.update).toHaveBeenCalledTimes(1);
  });

  it('언마운트하면 요청 signal이 abort된다', async () => {
    const commands = new FakeProductCommands();
    commands.update.mockReturnValue(new Promise(() => {}));
    const { wrapper } = setup(commands);
    const { result, unmount } = renderHook(() => useSaveProduct(), { wrapper });
    act(() => {
      void result.current.submit(breadProduct, { name: 'a' });
    });
    await waitFor(() => expect(commands.update).toHaveBeenCalledTimes(1));
    const signal = commands.update.mock.calls[0][2];
    unmount();
    expect(signal?.aborted).toBe(true);
  });
});
