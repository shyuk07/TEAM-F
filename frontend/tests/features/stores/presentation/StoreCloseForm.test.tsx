import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { StoreCloseForm } from '@/features/stores';
import { ApiError } from '@/shared/api/error';
import { closedStore } from '../../../entities/store/fakes/stores';
import { FakeStoreRepository } from '../../../entities/store/fakes/fakeStoreRepository.fake';
import { FakeStoreCommands } from '../fakes/fakeStoreCommands.fake';
import { renderStoresContainer } from './renderStores';

function renderForm(
  opts: { repo?: FakeStoreRepository; commands?: FakeStoreCommands; release?: () => void } = {},
) {
  const repo = opts.repo ?? new FakeStoreRepository();
  const commands = opts.commands ?? new FakeStoreCommands();
  const ctx = renderStoresContainer({ repo, commands });
  const onCancel = vi.fn();
  render(<StoreCloseForm store={closedStore} onCancel={onCancel} />, { wrapper: ctx.wrapper });
  return { ...ctx, onCancel, repo, commands, release: opts.release ?? (() => undefined) };
}

describe('features/stores presentation StoreCloseForm', () => {
  it('경고 문구와 확인 라벨(상점명 포함)이 보인다', () => {
    renderForm();
    expect(
      screen.getByText('폐점하면 다시 열 수 없고, 이 계정으로 새 상점도 만들 수 없어요.'),
    ).toBeInTheDocument();
    const label = screen.getByText(/확인을 위해 상점명을 입력하세요:/);
    expect(label).toHaveTextContent('망원베이커리');
  });

  it('본문 dk 버튼과 CtaBar 버튼 두 벌이 있다(getAllByRole)', () => {
    renderForm();
    expect(screen.getAllByRole('button', { name: '폐점하기' })).toHaveLength(2);
    expect(screen.getAllByRole('button', { name: '취소' })).toHaveLength(2);
  });

  it('처음에는 「폐점하기」가 aria-disabled이고, 상점명을 정확히 입력하면 활성화되고 한 글자를 지우면 다시 비활성', async () => {
    renderForm();
    const btn = screen.getAllByRole('button', { name: '폐점하기' })[0];
    expect(btn).toHaveAttribute('aria-disabled', 'true');
    const input = screen.getByLabelText(/확인을 위해 상점명을 입력하세요:/);
    await userEvent.type(input, '망원베이커리');
    await waitFor(() => expect(btn).not.toHaveAttribute('aria-disabled', 'true'));
    await userEvent.type(input, '간');
    await waitFor(() => expect(btn).toHaveAttribute('aria-disabled', 'true'));
  });

  it('비활성일 때 눌러도 close가 불리지 않는다', async () => {
    const { commands } = renderForm();
    await userEvent.click(screen.getAllByRole('button', { name: '폐점하기' })[0]);
    expect(commands.close).not.toHaveBeenCalled();
  });

  it('활성에서 클릭 → close(store.id) 1번, 제출 중 이름은 「처리 중…」', async () => {
    const { commands, release, repo } = renderForm(gate());
    await userEvent.type(screen.getByLabelText(/확인을 위해 상점명을 입력하세요:/), '망원베이커리');
    const click = userEvent.click(screen.getAllByRole('button', { name: '폐점하기' })[0]);
    expect(await screen.findAllByRole('button', { name: '처리 중…' })).toHaveLength(2);
    release();
    await click;
    expect(commands.close).toHaveBeenCalledTimes(1);
    expect(commands.close).toHaveBeenCalledWith(closedStore.id, expect.anything());
    await waitFor(() => expect(repo.findMine).toHaveBeenCalledTimes(2));
  });

  it('「취소」 클릭 → onCancel 호출. 제출 중에도 「취소」는 눌린다', async () => {
    const { commands, release, onCancel } = renderForm(gate());
    await userEvent.type(screen.getByLabelText(/확인을 위해 상점명을 입력하세요:/), '망원베이커리');
    const submitting = userEvent.click(screen.getAllByRole('button', { name: '폐점하기' })[0]);
    await screen.findAllByRole('button', { name: '처리 중…' });
    await userEvent.click(screen.getAllByRole('button', { name: '취소' })[0]);
    expect(onCancel).toHaveBeenCalledTimes(1);
    release();
    await submitting;
    expect(commands.close).toHaveBeenCalledTimes(1);
  });

  it('close 성공 후 findMine이 다시 불린다(폐점 뒤 가드가 /owner/start로 보낸다)', async () => {
    const { repo } = renderForm();
    await userEvent.type(screen.getByLabelText(/확인을 위해 상점명을 입력하세요:/), '망원베이커리');
    await userEvent.click(screen.getAllByRole('button', { name: '폐점하기' })[0]);
    await waitFor(() => expect(repo.findMine).toHaveBeenCalledTimes(2));
  });

  it('STORE_HAS_OPEN_OFFERS → alert에 서버 문구, 입력 유지, 「폐점하기」는 다시 활성', async () => {
    const commands = new FakeStoreCommands();
    commands.close.mockRejectedValue(
      new ApiError(400, 'STORE_HAS_OPEN_OFFERS', '진행 중인 할인이 있어요'),
    );
    renderForm({ repo: new FakeStoreRepository(), commands });
    const input = screen.getByRole('textbox');
    await userEvent.type(input, '망원베이커리');
    await userEvent.click(screen.getAllByRole('button', { name: '폐점하기' })[0]);
    expect(await screen.findByRole('alert')).toHaveTextContent('진행 중인 할인이 있어요');
    expect(input).toHaveValue('망원베이커리');
    await waitFor(() =>
      expect(screen.getAllByRole('button', { name: '폐점하기' })[0]).not.toHaveAttribute(
        'aria-disabled',
        'true',
      ),
    );
  });
});

function gate() {
  const commands = new FakeStoreCommands();
  let release!: () => void;
  const gatePromise = new Promise<void>((res) => {
    release = res;
  });
  commands.close.mockImplementation(() => gatePromise);
  return { commands, release: () => release() };
}
