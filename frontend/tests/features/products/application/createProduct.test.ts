import { describe, expect, it } from 'vitest';
import { ApiError } from '@/shared/api/error';
import { createProduct } from '@/features/products/application/createProduct';
import type { ProductFormValue } from '@/features/products/domain/productForm';
import { createdProduct } from '../../../entities/product/fakes/products';
import { FakeProductCommands } from '../fakes/fakeProductCommands.fake';

const value: ProductFormValue = {
  name: '식빵',
  originalPrice: 12000,
  category: null,
  description: null,
};

describe('features/products application createProduct', () => {
  it('commands.create를 (storeId, 입력, photo, signal)로 1번 부른다', async () => {
    const commands = new FakeProductCommands();
    const photo = new Blob([new Uint8Array(3)], { type: 'image/jpeg' });
    const ctrl = new AbortController();
    await createProduct({ commands }, { storeId: 's1', value, photo }, ctrl.signal);
    expect(commands.create).toHaveBeenCalledTimes(1);
    expect(commands.create).toHaveBeenCalledWith(
      's1',
      { name: '식빵', originalPrice: 12000, category: null, description: null },
      photo,
      ctrl.signal,
    );
  });

  it('사진이 없으면 photo는 null', async () => {
    const commands = new FakeProductCommands();
    await createProduct({ commands }, { storeId: 's1', value, photo: null });
    expect(commands.create.mock.calls[0][2]).toBeNull();
  });

  it('성공 값을 그대로 돌려준다', async () => {
    const commands = new FakeProductCommands();
    await expect(createProduct({ commands }, { storeId: 's1', value, photo: null })).resolves.toBe(
      createdProduct,
    );
  });

  it('실패하면 같은 오류를 던진다', async () => {
    const commands = new FakeProductCommands();
    const err = new ApiError(400, 'STORE_SUSPENDED', 'x');
    commands.create.mockRejectedValue(err);
    await expect(createProduct({ commands }, { storeId: 's1', value, photo: null })).rejects.toBe(
      err,
    );
    expect(commands.create).toHaveBeenCalledTimes(1);
  });
});
