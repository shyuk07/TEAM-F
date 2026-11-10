import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApprovalsPanel } from '@/features/admin';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../auth/fakes/deferred';
import { FakeAdminRepository, page, pendingOwner } from '../fakes/fakeAdminRepository.fake';
import { renderAdmin } from '../fakes/renderAdmin';

function repoWith(items = [pendingOwner]) {
  const repo = new FakeAdminRepository();
  repo.listUsers.mockImplementation((q) =>
    Promise.resolve(
      q.status === 'SUSPENDED' ? page([], 2) : q.size === 1 ? page([], 3) : page(items),
    ),
  );
  return repo;
}

describe('ApprovalsPanel (M1)', () => {
  it('로딩 중에는 뼈대를 보인다', () => {
    const repo = new FakeAdminRepository();
    repo.listUsers.mockReturnValue(deferred<never>().promise);
    renderAdmin(<ApprovalsPanel />, repo);
    expect(screen.getByLabelText('불러오는 중')).toBeInTheDocument();
  });

  it('승인 대기 상점주 목록과 건수를 보인다 (role=OWNER, status=PENDING)', async () => {
    const repo = repoWith();
    renderAdmin(<ApprovalsPanel />, repo);
    expect(await screen.findByText('한끼반찬')).toBeInTheDocument();
    expect(repo.listUsers).toHaveBeenCalledWith(
      { role: 'OWNER', status: 'PENDING', email: undefined, page: 1, size: 20 },
      expect.any(AbortSignal),
    );
    expect(screen.getByText('승인 대기', { selector: '.kv > span' }).nextSibling).toHaveTextContent(
      '3',
    );
    expect(screen.getByText('정지 회원').nextSibling).toHaveTextContent('2');
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });

  it('빈 목록 상태', async () => {
    renderAdmin(<ApprovalsPanel />, repoWith([]));
    expect(await screen.findByText('승인 대기 중인 상점주가 없어요')).toBeInTheDocument();
  });

  it('불러오기 실패 → 서버 문구 + 다시 시도', async () => {
    const repo = new FakeAdminRepository();
    repo.listUsers.mockRejectedValueOnce(new ApiError(403, 'FORBIDDEN', '접근 권한이 없습니다.'));
    renderAdmin(<ApprovalsPanel />, repo);
    const alerts = await screen.findAllByRole('alert');
    expect(alerts.some((a) => a.textContent === '접근 권한이 없습니다.')).toBe(true);
    const before = repo.listUsers.mock.calls.length;
    await userEvent.click(screen.getAllByRole('button', { name: '다시 시도' })[0]);
    await waitFor(() => expect(repo.listUsers.mock.calls.length).toBeGreaterThan(before));
  });

  it('승인은 한 번 탭으로 처리하고 목록을 다시 불러온다', async () => {
    const repo = repoWith();
    renderAdmin(<ApprovalsPanel />, repo);
    await userEvent.click(await screen.findByRole('button', { name: '한끼반찬 승인' }));
    expect(repo.approveOwner).toHaveBeenCalledWith(pendingOwner.id);
    await waitFor(() => expect(repo.listUsers.mock.calls.length).toBeGreaterThanOrEqual(6));
  });

  it('승인 실패 문구를 보인다', async () => {
    const repo = repoWith();
    repo.approveOwner.mockRejectedValue(
      new ApiError(400, 'OWNER_NOT_PENDING', '승인 대기 중인 상점주가 아닙니다.'),
    );
    renderAdmin(<ApprovalsPanel />, repo);
    await userEvent.click(await screen.findByRole('button', { name: '한끼반찬 승인' }));
    expect(await screen.findByText('승인 대기 중인 상점주가 아닙니다.')).toBeInTheDocument();
  });

  it('거부는 M2 시트를 열고 사유와 함께 보낸다', async () => {
    const repo = repoWith();
    renderAdmin(<ApprovalsPanel />, repo);
    await userEvent.click(await screen.findByRole('button', { name: '한끼반찬 거부' }));
    const dialog = screen.getByRole('dialog', { name: '상점주 거부' });
    await userEvent.type(within(dialog).getByLabelText('거부 사유 *'), '서류 불일치');
    await userEvent.click(within(dialog).getByRole('button', { name: '거부하기' }));
    expect(repo.rejectOwner).toHaveBeenCalledWith(pendingOwner.id, '서류 불일치');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('이메일 검색은 1페이지부터 다시 찾는다', async () => {
    const repo = repoWith();
    renderAdmin(<ApprovalsPanel />, repo);
    await screen.findByText('한끼반찬');
    await userEvent.type(screen.getByRole('searchbox'), ' owner1 {Enter}');
    await waitFor(() =>
      expect(repo.listUsers).toHaveBeenCalledWith(
        { role: 'OWNER', status: 'PENDING', email: 'owner1', page: 1, size: 20 },
        expect.any(AbortSignal),
      ),
    );
  });
});
