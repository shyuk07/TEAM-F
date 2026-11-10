import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { OwnerStartPage } from '@/pages/owner-start';
import type { User } from '@/features/auth';
import { ownerUser } from '../../../features/auth/fakes/users';
import { signedInFakes } from '../../../support/authFakes';
import { renderWithOwnerStore } from '../../../support/renderWithOwnerStore';
import { FakeStoreRepository } from '../../../entities/store/fakes/fakeStoreRepository.fake';
import { activeStore, closedStore } from '../../../entities/store/fakes/stores';

function renderAt(path = '/', user: User = ownerUser, repo = new FakeStoreRepository()) {
  return renderWithOwnerStore(<OwnerStartPage />, {
    initialEntries: [path],
    fakes: signedInFakes(user),
    repo,
  });
}

describe('pages/owner-start OwnerStartPage', () => {
  it('계정 PENDING + 상점 없음 → 「승인 대기 중이에요」, 폼 없음', async () => {
    renderAt('/', { ...ownerUser, status: 'PENDING' }, withNone());
    expect(await screen.findByText('승인 대기 중이에요')).toBeInTheDocument();
    expect(screen.queryByLabelText(/픽업 주소/)).toBeNull();
  });

  it('계정 REJECTED + 상점 없음 → 「가입이 거절되었습니다」', async () => {
    renderAt('/', { ...ownerUser, status: 'REJECTED' }, withNone());
    expect(await screen.findByText('가입이 거절되었습니다')).toBeInTheDocument();
  });

  it('계정 APPROVED + 상점 없음 → 「픽업 주소」 입력과 「상점 열기」가 있다', async () => {
    renderAt('/', ownerUser, withNone());
    expect(await screen.findByLabelText(/픽업 주소/)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '상점 열기' }).length).toBeGreaterThan(0);
  });

  it('상점 CLOSED → 「폐점한 상점이에요」, 폼 없음', async () => {
    const repo = new FakeStoreRepository();
    repo.findMine.mockResolvedValue(closedStore);
    renderAt('/', ownerUser, repo);
    expect(await screen.findByText('폐점한 상점이에요')).toBeInTheDocument();
    expect(screen.queryByLabelText(/픽업 주소/)).toBeNull();
  });

  it('계정 SUSPENDED + 상점 없음 → 「정지」 태그만(도달 불가 분기)', async () => {
    renderAt('/', { ...ownerUser, status: 'SUSPENDED' } as User, withNone());
    expect(await screen.findByText('정지')).toBeInTheDocument();
    expect(screen.queryByText('승인 대기 중이에요')).toBeNull();
  });

  it('어느 경우든 「마감직전 상점주」 로고와 「로그아웃」이 있고, 「로그아웃」은 확인 시트를 연다', async () => {
    renderAt('/', ownerUser, withNone());
    expect(await screen.findByText('마감직전 상점주')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('로그아웃할까요?');
  });

  it('상점 ACTIVE일 때(가드가 오기 전 한 프레임) 본문이 비어 있다', async () => {
    const repo = new FakeStoreRepository();
    repo.findMine.mockResolvedValue(activeStore);
    renderAt('/', ownerUser, repo);
    await waitFor(() => expect(screen.queryByText('마감직전 상점주')).not.toBeNull());
    expect(screen.queryByLabelText(/픽업 주소/)).toBeNull();
    expect(screen.queryByRole('button', { name: '상점 열기' })).toBeNull();
  });
});

function withNone() {
  const repo = new FakeStoreRepository();
  repo.findMine.mockResolvedValue(null);
  return repo;
}
