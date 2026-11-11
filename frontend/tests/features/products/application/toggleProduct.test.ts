import { describe, expect, it } from 'vitest';
import { ApiError } from '@/shared/api/error';
import { toggleProduct } from '@/features/products/application/toggleProduct';
import { baguetteProduct, breadProduct } from '../../../entities/product/fakes/products';
import { FakeProductCommands } from '../fakes/fakeProductCommands.fake';

describe('features/products application toggleProduct', () => {
  it('노출 상품 → deactivate(id)만 부른다(확인 단계 없음)', async () => {
    const commands = new FakeProductCommands();
    const ctrl = new AbortController();
    await toggleProduct({ commands }, breadProduct, ctrl.signal);
    expect(commands.deactivate).toHaveBeenCalledTimes(1);
    expect(commands.deactivate).toHaveBeenCalledWith('p1', ctrl.signal);
    expect(commands.activate).not.toHaveBeenCalled();
  });

  it('숨김 상품 → activate(id)만 부른다', async () => {
    const commands = new FakeProductCommands();
    await toggleProduct({ commands }, baguetteProduct);
    expect(commands.activate).toHaveBeenCalledTimes(1);
    expect(commands.activate.mock.calls[0][0]).toBe('p2');
    expect(commands.deactivate).not.toHaveBeenCalled();
  });

  it('응답 Product를 그대로 돌려준다', async () => {
    const commands = new FakeProductCommands();
    const hidden = { ...breadProduct, isActive: false };
    commands.deactivate.mockResolvedValue(hidden);
    await expect(toggleProduct({ commands }, breadProduct)).resolves.toBe(hidden);
  });

  // B1(D-33)
  it('노출 상품의 deactivate가 PRODUCT_ALREADY_INACTIVE로 reject되면 던지지 않고 isActive:false를 resolve한다', async () => {
    const commands = new FakeProductCommands();
    commands.deactivate.mockRejectedValue(new ApiError(400, 'PRODUCT_ALREADY_INACTIVE', 'x'));
    await expect(toggleProduct({ commands }, breadProduct)).resolves.toEqual({
      ...breadProduct,
      isActive: false,
    });
  });

  it('숨김 상품의 activate가 PRODUCT_ALREADY_ACTIVE로 reject되면 isActive:true를 resolve한다', async () => {
    const commands = new FakeProductCommands();
    commands.activate.mockRejectedValue(new ApiError(400, 'PRODUCT_ALREADY_ACTIVE', 'x'));
    await expect(toggleProduct({ commands }, baguetteProduct)).resolves.toEqual({
      ...baguetteProduct,
      isActive: true,
    });
  });

  it('abort로 reject된 오류는 그대로 던진다', async () => {
    const commands = new FakeProductCommands();
    const abortErr = new DOMException('aborted', 'AbortError');
    commands.deactivate.mockRejectedValue(abortErr);
    await expect(toggleProduct({ commands }, breadProduct)).rejects.toBe(abortErr);
  });

  it('오류를 그대로 던진다', async () => {
    const commands = new FakeProductCommands();
    const err = new ApiError(400, 'PRODUCT_HAS_OPEN_OFFER', 'x');
    commands.deactivate.mockRejectedValue(err);
    await expect(toggleProduct({ commands }, breadProduct)).rejects.toBe(err);
  });
});
