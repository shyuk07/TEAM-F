import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ApiError } from '@/shared/api/error';
import { useToggleProduct } from '@/features/products/application/useToggleProduct';
import { baguetteProduct, breadProduct } from '../../../entities/product/fakes/products';
import { FakeProductCommands } from '../fakes/fakeProductCommands.fake';
import { createProductsContainer } from '../fakes/renderProducts';

function setup(commands = new FakeProductCommands()) {
  const { wrapper } = createProductsContainer({
    repo: createProductsContainer().repo,
    commands,
  });
  return { commands, wrapper };
}

describe('features/products application useToggleProduct', () => {
  it('노출 상품 toggle → deactivate 호출, isActive:false Product를 resolve하고 idle', async () => {
    const { commands, wrapper } = setup();
    const { result } = renderHook(() => useToggleProduct(), { wrapper });
    await act(async () => {
      const p = await result.current.toggle(breadProduct);
      expect(p?.isActive).toBe(false);
    });
    expect(commands.deactivate.mock.calls[0][0]).toBe('p1');
    expect(commands.activate).not.toHaveBeenCalled();
    expect(result.current.status).toBe('idle');
  });

  it('숨김 상품 toggle → activate 호출', async () => {
    const { commands, wrapper } = setup();
    const { result } = renderHook(() => useToggleProduct(), { wrapper });
    await act(async () => {
      await result.current.toggle(baguetteProduct);
    });
    expect(commands.activate.mock.calls[0][0]).toBe('p2');
    expect(commands.deactivate).not.toHaveBeenCalled();
  });

  it('PRODUCT_HAS_OPEN_OFFER: null을 resolve, status=error, 숨기기 거절 문구', async () => {
    const commands = new FakeProductCommands();
    commands.deactivate.mockRejectedValue(new ApiError(400, 'PRODUCT_HAS_OPEN_OFFER', 'x'));
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useToggleProduct(), { wrapper });
    await act(async () => {
      await expect(result.current.toggle(breadProduct)).resolves.toBeNull();
    });
    expect(result.current.status).toBe('error');
    expect(result.current.errorMessage).toBe(
      '진행 중인 할인이 있어 숨길 수 없어요. 판매를 중단한 뒤 다시 숨겨 주세요.',
    );
  });

  // B1(D-33): 이미 원하는 상태면 성공으로 처리해 그 상태의 Product를 돌려준다
  it.each([
    ['PRODUCT_ALREADY_INACTIVE', breadProduct, false],
    ['PRODUCT_ALREADY_ACTIVE', baguetteProduct, true],
  ])(
    '%s: 그 상태의 Product를 resolve하고 idle, errorMessage null',
    async (code, product, active) => {
      const commands = new FakeProductCommands();
      commands.deactivate.mockRejectedValue(new ApiError(400, code, 'x'));
      commands.activate.mockRejectedValue(new ApiError(400, code, 'x'));
      const { wrapper } = setup(commands);
      const { result } = renderHook(() => useToggleProduct(), { wrapper });
      await act(async () => {
        await expect(result.current.toggle(product)).resolves.toEqual({
          ...product,
          isActive: active,
        });
      });
      expect(result.current.errorMessage).toBeNull();
      expect(result.current.status).toBe('idle');
    },
  );

  it('pending 중 재호출은 무시된다', async () => {
    const commands = new FakeProductCommands();
    commands.deactivate.mockReturnValue(new Promise(() => {}));
    const { wrapper } = setup(commands);
    const { result } = renderHook(() => useToggleProduct(), { wrapper });
    act(() => {
      void result.current.toggle(breadProduct);
    });
    await waitFor(() => expect(result.current.status).toBe('pending'));
    act(() => {
      void result.current.toggle(breadProduct);
    });
    expect(commands.deactivate).toHaveBeenCalledTimes(1);
  });
});
