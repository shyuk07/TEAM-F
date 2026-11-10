import { describe, expect, it } from 'vitest';
import { closeStore } from '@/features/stores/application/closeStore';
import { activeStore, closedStore } from '../../../entities/store/fakes/stores';
import { FakeStoreCommands } from '../fakes/fakeStoreCommands.fake';

describe('features/stores application closeStore', () => {
  it('이름이 불일치하면 Error를 던지고 commands.close를 부르지 않는다', async () => {
    const commands = new FakeStoreCommands();
    await expect(
      closeStore({ commands }, { store: activeStore, typedName: '망원베이커' }),
    ).rejects.toThrow();
    expect(commands.close).not.toHaveBeenCalled();
  });

  it('이름이 일치하면 commands.close(store.id)를 1번 부른다', async () => {
    const commands = new FakeStoreCommands();
    const ctrl = new AbortController();
    await closeStore({ commands }, { store: closedStore, typedName: '망원베이커리' }, ctrl.signal);
    expect(commands.close).toHaveBeenCalledTimes(1);
    expect(commands.close).toHaveBeenCalledWith(closedStore.id, ctrl.signal);
  });

  it('포트 오류는 그대로 던진다', async () => {
    const commands = new FakeStoreCommands();
    const err = new Error('boom');
    commands.close.mockRejectedValue(err);
    await expect(
      closeStore({ commands }, { store: closedStore, typedName: '망원베이커리' }),
    ).rejects.toBe(err);
  });
});
