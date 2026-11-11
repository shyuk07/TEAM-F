import type { ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MyStoreProvider, StoreRepositoryToken } from '@/entities/store';
import { StoreCommandsToken } from '@/features/stores/application/tokens';
import { useCloseStore } from '@/features/stores/application/useCloseStore';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { bind, Container } from '@/shared/lib/di';
import { ApiError } from '@/shared/api/error';
import { closedStore } from '../../../entities/store/fakes/stores';
import { FakeStoreRepository } from '../../../entities/store/fakes/fakeStoreRepository.fake';
import { FakeStoreCommands } from '../fakes/fakeStoreCommands.fake';

function wrapperWith(
  fakes = { repo: new FakeStoreRepository(), commands: new FakeStoreCommands() },
) {
  const container = new Container([
    bind(StoreRepositoryToken, fakes.repo),
    bind(StoreCommandsToken, fakes.commands),
  ]);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={container}>
      <MyStoreProvider>{children}</MyStoreProvider>
    </DepsProvider>
  );
  return { wrapper, ...fakes };
}

describe('features/stores application useCloseStore', () => {
  it('성공하면 findMine이 다시 불린다(reload)', async () => {
    const { wrapper, repo, commands } = wrapperWith();
    const { result } = renderHook(() => useCloseStore(closedStore), { wrapper });
    await act(async () => {
      await result.current.submit('망원베이커리');
    });
    expect(commands.close).toHaveBeenCalledTimes(1);
    expect(repo.findMine).toHaveBeenCalledTimes(2);
  });

  it('STORE_HAS_OPEN_OFFERS는 서버 문구를 표시하고 findMine 추가 호출이 없다', async () => {
    const commands = new FakeStoreCommands();
    commands.close.mockRejectedValue(
      new ApiError(400, 'STORE_HAS_OPEN_OFFERS', '진행 중인 할인이 있어요'),
    );
    const { wrapper, repo } = wrapperWith({ repo: new FakeStoreRepository(), commands });
    const { result } = renderHook(() => useCloseStore(closedStore), { wrapper });
    await act(async () => {
      await result.current.submit('망원베이커리').catch(() => undefined);
    });
    expect(result.current.errorMessage).toBe('진행 중인 할인이 있어요');
    expect(repo.findMine).toHaveBeenCalledTimes(1);
  });

  it('STORE_ALREADY_CLOSED는 문구를 표시하고 findMine을 다시 불린다', async () => {
    const commands = new FakeStoreCommands();
    commands.close.mockRejectedValue(new ApiError(409, 'STORE_ALREADY_CLOSED', ''));
    const { wrapper, repo } = wrapperWith({ repo: new FakeStoreRepository(), commands });
    const { result } = renderHook(() => useCloseStore(closedStore), { wrapper });
    await act(async () => {
      await result.current.submit('망원베이커리').catch(() => undefined);
    });
    expect(result.current.errorMessage).toBe(
      '상점을 폐점하지 못했어요. 잠시 후 다시 시도해 주세요.',
    );
    expect(repo.findMine).toHaveBeenCalledTimes(2);
  });

  it('pending 중에는 pending=true이고 끝나면 false가 된다', async () => {
    const commands = new FakeStoreCommands();
    let release!: () => void;
    const gate = new Promise<void>((res) => {
      release = res;
    });
    commands.close.mockImplementation(() => gate);
    const { wrapper } = wrapperWith({ repo: new FakeStoreRepository(), commands });
    const { result } = renderHook(() => useCloseStore(closedStore), { wrapper });
    let submit!: Promise<void>;
    await act(async () => {
      submit = result.current.submit('망원베이커리');
    });
    await waitFor(() => expect(result.current.pending).toBe(true));
    await act(async () => {
      release();
      await submit;
    });
    expect(result.current.pending).toBe(false);
  });

  it('이름이 틀려도 훅은 포트를 부르지 않는다(검증은 application 몫)', async () => {
    const { wrapper, commands } = wrapperWith();
    const { result } = renderHook(() => useCloseStore(closedStore), { wrapper });
    await act(async () => {
      await expect(result.current.submit('다른 이름')).rejects.toThrow();
    });
    expect(commands.close).not.toHaveBeenCalled();
  });
});
