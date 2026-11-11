import { describe, expect, it } from 'vitest';
import { ApiError } from '@/shared/api/error';
import { saveProduct } from '@/features/products/application/saveProduct';
import { breadProduct } from '../../../entities/product/fakes/products';
import { FakeProductCommands } from '../fakes/fakeProductCommands.fake';

describe('features/products application saveProduct', () => {
  it('변경이 있으면 update(original.id, changes)를 1번 부르고 그 응답을 돌려준다', async () => {
    const commands = new FakeProductCommands();
    const updated = { ...breadProduct, name: '새 이름' };
    commands.update.mockResolvedValue(updated);
    const ctrl = new AbortController();
    const result = await saveProduct(
      { commands },
      { original: breadProduct, changes: { name: '새 이름' } },
      ctrl.signal,
    );
    expect(commands.update).toHaveBeenCalledTimes(1);
    expect(commands.update).toHaveBeenCalledWith('p1', { name: '새 이름' }, ctrl.signal);
    expect(result).toBe(updated);
    expect(commands.create).not.toHaveBeenCalled();
    expect(commands.deactivate).not.toHaveBeenCalled();
  });

  it('변경이 없으면({}) 아무것도 부르지 않고 original을 돌려준다', async () => {
    const commands = new FakeProductCommands();
    const result = await saveProduct({ commands }, { original: breadProduct, changes: {} });
    expect(result).toBe(breadProduct);
    expect(commands.update).not.toHaveBeenCalled();
    expect(commands.create).not.toHaveBeenCalled();
    expect(commands.deactivate).not.toHaveBeenCalled();
    expect(commands.activate).not.toHaveBeenCalled();
  });

  it('update가 실패하면 같은 오류를 던진다', async () => {
    const commands = new FakeProductCommands();
    const err = new ApiError(400, 'VALIDATION_ERROR', 'x');
    commands.update.mockRejectedValue(err);
    await expect(
      saveProduct({ commands }, { original: breadProduct, changes: { originalPrice: 1 } }),
    ).rejects.toBe(err);
  });

  it('{category: null}은 그대로 update에 전달되고 다른 필드에 null을 만들어 넣지 않는다', async () => {
    const commands = new FakeProductCommands();
    await saveProduct({ commands }, { original: breadProduct, changes: { category: null } });
    const sent = commands.update.mock.calls[0][1];
    expect(sent).toEqual({ category: null });
    expect(Object.keys(sent)).toEqual(['category']);
  });
});
