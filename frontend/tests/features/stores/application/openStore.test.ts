import { describe, expect, it } from 'vitest';
import { openStore } from '@/features/stores/application/openStore';
import { activeStore } from '../../../entities/store/fakes/stores';
import { FakeStoreCommands } from '../fakes/fakeStoreCommands.fake';

describe('features/stores application openStore', () => {
  it('빈 주소는 Error를 던지고 commands.open을 부르지 않는다', async () => {
    const commands = new FakeStoreCommands();
    await expect(openStore({ commands }, { pickupAddress: '' })).rejects.toThrow();
    expect(commands.open).not.toHaveBeenCalled();
  });

  it(' 앞뒤 공백을 지운 주소로 commands.open을 부른다', async () => {
    const commands = new FakeStoreCommands();
    const ctrl = new AbortController();
    await openStore({ commands }, { pickupAddress: ' 서울 ' }, ctrl.signal);
    expect(commands.open).toHaveBeenCalledWith('서울', ctrl.signal);
  });

  it('성공하면 Store를 돌려준다', async () => {
    const commands = new FakeStoreCommands();
    commands.open.mockResolvedValue(activeStore);
    await expect(openStore({ commands }, { pickupAddress: '서울' })).resolves.toBe(activeStore);
  });

  it('포트 오류는 그대로 던진다', async () => {
    const commands = new FakeStoreCommands();
    const err = new Error('boom');
    commands.open.mockRejectedValue(err);
    await expect(openStore({ commands }, { pickupAddress: '서울' })).rejects.toBe(err);
  });
});
