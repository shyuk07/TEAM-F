import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { StoreOpenForm } from '@/features/stores';
import { ApiError } from '@/shared/api/error';
import type { Store } from '@/entities/store';
import { FakeStoreRepository } from '../../../entities/store/fakes/fakeStoreRepository.fake';
import { activeStore } from '../../../entities/store/fakes/stores';
import { FakeStoreCommands } from '../fakes/fakeStoreCommands.fake';
import { renderStoresContainer } from './renderStores';

const OWNER_NAME = '망원베이커리';
const OPEN_ERROR = '지금은 주소를 확인할 수 없어요. 잠시 후 다시 시도해 주세요.';

function renderForm(
  fakes = { repo: new FakeStoreRepository(), commands: new FakeStoreCommands() },
) {
  const ctx = renderStoresContainer(fakes);
  render(<StoreOpenForm ownerName={OWNER_NAME} />, { wrapper: ctx.wrapper });
  return { ...ctx, repo: fakes.repo, commands: fakes.commands };
}

function gateCommands() {
  const commands = new FakeStoreCommands();
  let release!: () => void;
  const gate = new Promise<void>((res) => {
    release = res;
  });
  commands.open.mockImplementation(() => gate.then(() => activeStore));
  return { commands, release };
}

describe('features/stores presentation StoreOpenForm', () => {
  it('「픽업 주소 *」 입력과 「상점 열기」 버튼 두 개(getAllByRole)가 있다. 편집할 수 있는 「상점명」 입력은 없다', () => {
    renderForm();
    expect(screen.getByLabelText(/픽업 주소 \*/)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '상점 열기' })).toHaveLength(2);
    expect(screen.queryByLabelText('상점명')).toBeNull();
  });

  it('「상점명 (가입 시 상호)」 읽기 전용 입력에 계정 이름이 보이고 편집할 수 없다', () => {
    renderForm();
    const input = screen.getByLabelText('상점명 (가입 시 상호)');
    expect(input).toHaveValue(OWNER_NAME);
    expect(input).toHaveAttribute('readonly');
  });

  it('ownerName이 ""(name null 방어, D-21)이면 폼 대신 개설 불가 안내가 보이고 「픽업 주소」·「상점 열기」가 없다', () => {
    const ctx = renderStoresContainer();
    render(<StoreOpenForm ownerName="" />, { wrapper: ctx.wrapper });
    expect(screen.getByText('계정 정보가 올바르지 않아 상점을 열 수 없어요.')).toBeInTheDocument();
    expect(screen.queryByLabelText(/픽업 주소/)).toBeNull();
    expect(screen.queryByRole('button', { name: '상점 열기' })).toBeNull();
  });

  it('입력이 비어 있으면 두 버튼 모두 aria-disabled=true이고, 글자를 입력하면 해제된다', async () => {
    renderForm();
    for (const btn of screen.getAllByRole('button', { name: '상점 열기' })) {
      expect(btn).toHaveAttribute('aria-disabled', 'true');
    }
    await userEvent.type(screen.getByLabelText(/픽업 주소/), '서울시 마포구');
    await waitFor(() => {
      for (const btn of screen.getAllByRole('button', { name: '상점 열기' })) {
        expect(btn).not.toHaveAttribute('aria-disabled', 'true');
      }
    });
  });

  it('비활성일 때 눌러도 open이 불리지 않는다', async () => {
    const { commands } = renderForm();
    await userEvent.click(screen.getAllByRole('button', { name: '상점 열기' })[0]);
    expect(commands.open).not.toHaveBeenCalled();
  });

  it('입력 후 첫 번째 버튼 클릭 → open(입력값) 1번', async () => {
    const { commands } = renderForm();
    await userEvent.type(screen.getByLabelText(/픽업 주소/), '서울시 마포구 망원로 10');
    await userEvent.click(screen.getAllByRole('button', { name: '상점 열기' })[0]);
    expect(commands.open).toHaveBeenCalledTimes(1);
    expect(commands.open).toHaveBeenCalledWith('서울시 마포구 망원로 10', expect.anything());
  });

  it('두 번째(CtaBar) 버튼도 같은 폼을 제출한다', async () => {
    const { commands } = renderForm();
    await userEvent.type(screen.getByLabelText(/픽업 주소/), '서울시 마포구 망원로 10');
    await userEvent.click(screen.getAllByRole('button', { name: '상점 열기' })[1]);
    expect(commands.open).toHaveBeenCalledTimes(1);
  });

  it('제출 중 버튼 이름이 「처리 중…」이고 두 번 클릭해도 한 번만 호출된다', async () => {
    const { commands, release } = gateCommands();
    renderForm({ repo: new FakeStoreRepository(), commands });
    await userEvent.type(screen.getByLabelText(/픽업 주소/), '서울');
    const click = userEvent.click(screen.getAllByRole('button', { name: '상점 열기' })[0]);
    expect(await screen.findAllByRole('button', { name: '처리 중…' })).toHaveLength(2);
    await userEvent.click((await screen.findAllByRole('button', { name: '처리 중…' }))[0]);
    release();
    await click;
    expect(commands.open).toHaveBeenCalledTimes(1);
  });

  it('GEOCODING_UNAVAILABLE 응답 → alert에 정본 문구, 입력값은 유지된다', async () => {
    const commands = new FakeStoreCommands();
    commands.open.mockRejectedValue(new ApiError(503, 'GEOCODING_UNAVAILABLE', '서버 문구'));
    renderForm({ repo: new FakeStoreRepository(), commands });
    await userEvent.type(screen.getByLabelText(/픽업 주소/), '서울시 마포구 망원로 10');
    await userEvent.click(screen.getAllByRole('button', { name: '상점 열기' })[0]);
    expect(await screen.findByRole('alert')).toHaveTextContent(OPEN_ERROR);
    expect(screen.getByLabelText(/픽업 주소/)).toHaveValue('서울시 마포구 망원로 10');
  });

  it('성공하면 findMine이 다시 불린다', async () => {
    const { repo } = renderForm();
    await userEvent.type(screen.getByLabelText(/픽업 주소/), '서울시 마포구 망원로 10');
    await userEvent.click(screen.getAllByRole('button', { name: '상점 열기' })[0]);
    await waitFor(() => expect(repo.findMine).toHaveBeenCalledTimes(2));
    void ({} as Store);
  });

  it('입력에 maxLength 500이 걸려 있다', () => {
    renderForm();
    expect(screen.getByLabelText(/픽업 주소/)).toHaveAttribute('maxlength', '500');
  });
});
