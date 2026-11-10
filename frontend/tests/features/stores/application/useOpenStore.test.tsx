import type { ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MyStoreProvider, StoreRepositoryToken } from '@/entities/store';
import { StoreCommandsToken } from '@/features/stores/application/tokens';
import { useOpenStore } from '@/features/stores/application/useOpenStore';
import { activeStore } from '../../../entities/store/fakes/stores';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { bind, Container } from '@/shared/lib/di';
import { ApiError } from '@/shared/api/error';
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

describe('features/stores application useOpenStore', () => {
  it('초기 pending은 false이고 errorMessage는 null이다', async () => {
    const { wrapper } = wrapperWith();
    const { result } = renderHook(() => useOpenStore(), { wrapper });
    await act(() => Promise.resolve());
    expect(result.current.pending).toBe(false);
    expect(result.current.errorMessage).toBeNull();
  });

  it('성공하면 findMine이 다시 불린다(reload)', async () => {
    const { wrapper, repo, commands } = wrapperWith();
    const { result } = renderHook(() => useOpenStore(), { wrapper });
    await act(async () => {
      await result.current.submit('서울시 마포구 망원로 10');
    });
    expect(commands.open).toHaveBeenCalledTimes(1);
    expect(repo.findMine).toHaveBeenCalledTimes(2);
    expect(result.current.pending).toBe(false);
    expect(result.current.errorMessage).toBeNull();
  });

  it('pending 중에는 pending=true이고 끝나면 false가 된다', async () => {
    const commands = new FakeStoreCommands();
    const repo = new FakeStoreRepository();
    let release!: () => void;
    const gate = new Promise<void>((res) => {
      release = res;
    });
    commands.open.mockImplementation(() => gate.then(() => Promise.resolve(activeStore)));
    const { wrapper } = wrapperWith({ repo, commands });
    const { result } = renderHook(() => useOpenStore(), { wrapper });
    let submit!: Promise<void>;
    await act(async () => {
      submit = result.current.submit('서울');
    });
    await waitFor(() => expect(result.current.pending).toBe(true));
    await act(async () => {
      release();
      await submit;
    });
    expect(result.current.pending).toBe(false);
  });

  it('GEOCODING_UNAVAILABLE은 정본 문구를 errorMessage에 넣고 findMine 추가 호출이 없다', async () => {
    const commands = new FakeStoreCommands();
    commands.open.mockRejectedValue(new ApiError(503, 'GEOCODING_UNAVAILABLE', '서버 문구'));
    const { wrapper, repo } = wrapperWith({ repo: new FakeStoreRepository(), commands });
    const { result } = renderHook(() => useOpenStore(), { wrapper });
    await act(async () => {
      await result.current.submit('서울').catch(() => undefined);
    });
    expect(result.current.errorMessage).toBe(
      '지금은 주소를 확인할 수 없어요. 잠시 후 다시 시도해 주세요.',
    );
    expect(repo.findMine).toHaveBeenCalledTimes(1);
  });

  it('ADDRESS_NOT_FOUND는 서버 문구를 그대로 표시한다', async () => {
    const commands = new FakeStoreCommands();
    commands.open.mockRejectedValue(
      new ApiError(400, 'ADDRESS_NOT_FOUND', '주소를 찾을 수 없습니다.'),
    );
    const { wrapper } = wrapperWith({ repo: new FakeStoreRepository(), commands });
    const { result } = renderHook(() => useOpenStore(), { wrapper });
    await act(async () => {
      await result.current.submit('서울').catch(() => undefined);
    });
    expect(result.current.errorMessage).toBe('주소를 찾을 수 없습니다.');
  });

  it('STORE_ALREADY_EXISTS는 문구를 표시하고 findMine을 다시 불린다', async () => {
    const commands = new FakeStoreCommands();
    commands.open.mockRejectedValue(new ApiError(400, 'STORE_ALREADY_EXISTS', ''));
    const { wrapper, repo } = wrapperWith({ repo: new FakeStoreRepository(), commands });
    const { result } = renderHook(() => useOpenStore(), { wrapper });
    await act(async () => {
      await result.current.submit('서울').catch(() => undefined);
    });
    expect(result.current.errorMessage).toBe('상점을 열지 못했어요. 잠시 후 다시 시도해 주세요.');
    expect(repo.findMine).toHaveBeenCalledTimes(2);
  });

  it('다시 submit하면 이전 오류가 지워진다', async () => {
    const commands = new FakeStoreCommands();
    commands.open.mockRejectedValueOnce(new ApiError(400, 'ADDRESS_NOT_FOUND', '실패 문구'));
    const { wrapper } = wrapperWith({ repo: new FakeStoreRepository(), commands });
    const { result } = renderHook(() => useOpenStore(), { wrapper });
    await act(async () => {
      await result.current.submit('서울').catch(() => undefined);
    });
    expect(result.current.errorMessage).toBe('실패 문구');
    await act(async () => {
      await result.current.submit('서울');
    });
    expect(result.current.errorMessage).toBeNull();
  });

  it('pending 중 두 번째 submit은 포트를 한 번만 부른다', async () => {
    const commands = new FakeStoreCommands();
    const repo = new FakeStoreRepository();
    let release!: () => void;
    const gate = new Promise<void>((res) => {
      release = res;
    });
    commands.open.mockImplementation(() => gate.then(() => Promise.resolve(activeStore)));
    const { wrapper } = wrapperWith({ repo, commands });
    const { result } = renderHook(() => useOpenStore(), { wrapper });
    let first!: Promise<void>;
    await act(async () => {
      first = result.current.submit('서울');
    });
    await act(async () => {
      await result.current.submit('서울');
      release();
      await first;
    });
    expect(commands.open).toHaveBeenCalledTimes(1);
  });

  it('언마운트 뒤 요청이 끝나도 상태를 바꾸지 않는다(경고 없음)', async () => {
    const commands = new FakeStoreCommands();
    let release!: () => void;
    const gate = new Promise<void>((res) => {
      release = res;
    });
    commands.open.mockImplementation(() => gate.then(() => Promise.resolve(activeStore)));
    const { wrapper } = wrapperWith({ repo: new FakeStoreRepository(), commands });
    const { result, unmount } = renderHook(() => useOpenStore(), { wrapper });
    let pending!: Promise<void>;
    await act(async () => {
      pending = result.current.submit('서울');
    });
    unmount();
    await act(async () => {
      release();
      await pending;
    });
    expect(commands.open).toHaveBeenCalledTimes(1);
  });
});
