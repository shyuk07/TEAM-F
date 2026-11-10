import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { StoreClosePage } from '@/pages/store-close';
import { ownerUser } from '../../../features/auth/fakes/users';
import { signedInFakes } from '../../../support/authFakes';
import { renderWithOwnerStore } from '../../../support/renderWithOwnerStore';
import { FakeStoreRepository } from '../../../entities/store/fakes/fakeStoreRepository.fake';
import { activeStore } from '../../../entities/store/fakes/stores';

function renderAt() {
  const repo = new FakeStoreRepository();
  return renderWithOwnerStore(<StoreClosePage />, {
    initialEntries: ['/owner/store/close'],
    fakes: signedInFakes(ownerUser),
    repo,
  });
}

describe('pages/store-close StoreClosePage', () => {
  it('「상점 폐점」 제목이 있고 상점명이 라벨에 보인다', async () => {
    renderAt();
    expect(await screen.findByText('상점 폐점')).toBeInTheDocument();
    expect(screen.getByText(/확인을 위해 상점명을 입력하세요:/)).toHaveTextContent(
      /망원베이커리/,
    );
  });

  it('「뒤로」 클릭 → /owner/store로 이동한다', async () => {
    const { router } = renderAt();
    await screen.findByText('상점 폐점');
    await userEvent.click(screen.getByRole('link', { name: '뒤로' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/store'));
  });

  it('「취소」 클릭 → /owner/store로 이동한다', async () => {
    const { router } = renderAt();
    await screen.findByText('상점 폐점');
    await userEvent.click(screen.getAllByRole('button', { name: '취소' })[0]);
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/store'));
  });

  it('폐점 성공 후 findMine이 다시 불린다', async () => {
    const { repo } = renderAt();
    await screen.findByText('상점 폐점');
    await userEvent.type(screen.getByLabelText(/확인을 위해 상점명을 입력하세요:/), '망원베이커리');
    await userEvent.click(screen.getAllByRole('button', { name: '폐점하기' })[0]);
    await waitFor(() => expect(repo.findMine).toHaveBeenCalledTimes(2));
    void activeStore;
  });
});
