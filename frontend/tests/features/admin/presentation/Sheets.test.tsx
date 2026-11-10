import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PointGrantSheet } from '@/features/admin/presentation/PointGrantSheet';
import { SanctionSheet } from '@/features/admin/presentation/SanctionSheet';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../auth/fakes/deferred';
import { FakeAdminRepository } from '../fakes/fakeAdminRepository.fake';
import { renderAdmin } from '../fakes/renderAdmin';

const target = { id: 'u1', label: '박고객 (customer3@example.com)' };

describe('SanctionSheet (M2)', () => {
  it('회원 정지: 제목·라벨·버튼 문구, 정지 종료 칸', () => {
    renderAdmin(
      <SanctionSheet kind="suspendUser" target={target} onClose={vi.fn()} onDone={vi.fn()} />,
    );
    expect(screen.getByRole('dialog', { name: '회원 정지' })).toBeInTheDocument();
    expect(screen.getByText('대상: 박고객 (customer3@example.com)')).toBeInTheDocument();
    expect(screen.getByLabelText('정지 사유 *')).toHaveFocus();
    expect(screen.getByLabelText('정지 종료 (비우면 무기한)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '정지하기' })).toBeInTheDocument();
  });

  it('포인트 지급 시트도 첫 칸(지급 포인트)에 포커스', () => {
    renderAdmin(
      <PointGrantSheet
        target={{ id: 'u1', name: 'n', email: 'e', balance: 0 }}
        onClose={vi.fn()}
        onDone={vi.fn()}
      />,
    );
    expect(screen.getByLabelText('지급 포인트 * (1 이상)')).toHaveFocus();
  });

  it('정지가 아닌 제재에는 정지 종료 칸이 없다', () => {
    renderAdmin(
      <SanctionSheet kind="closeStore" target={target} onClose={vi.fn()} onDone={vi.fn()} />,
    );
    expect(screen.queryByLabelText('정지 종료 (비우면 무기한)')).not.toBeInTheDocument();
  });

  it('사유가 없으면 보내지 않고 오류를 보인다', async () => {
    const { repo } = renderAdmin(
      <SanctionSheet kind="suspendUser" target={target} onClose={vi.fn()} onDone={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole('button', { name: '정지하기' }));
    expect(screen.getByRole('alert')).toHaveTextContent('사유를 입력해 주세요.');
    expect(repo.suspendUser).not.toHaveBeenCalled();
  });

  it('성공하면 onDone, 처리 중에는 「처리 중…」이고 두 번 보내지 않는다', async () => {
    const repo = new FakeAdminRepository();
    const d = deferred<void>();
    repo.suspendUser.mockReturnValue(d.promise);
    const onDone = vi.fn();
    renderAdmin(
      <SanctionSheet kind="suspendUser" target={target} onClose={vi.fn()} onDone={onDone} />,
      repo,
    );
    await userEvent.type(screen.getByLabelText('정지 사유 *'), '노쇼 반복');
    await userEvent.click(screen.getByRole('button', { name: '정지하기' }));
    const busy = screen.getByRole('button', { name: '처리 중…' });
    await userEvent.click(busy);
    expect(repo.suspendUser).toHaveBeenCalledTimes(1);
    expect(repo.suspendUser).toHaveBeenCalledWith('u1', '노쇼 반복', null);
    d.resolve();
    await waitFor(() => expect(onDone).toHaveBeenCalledWith({ kind: 'user' }));
  });

  it('처리 중에는 Esc·딤·취소로 닫히지 않는다(다시 열어 두 번 보내지 못하게)', async () => {
    const repo = new FakeAdminRepository();
    const d = deferred<void>();
    repo.suspendUser.mockReturnValue(d.promise);
    const onClose = vi.fn();
    renderAdmin(
      <SanctionSheet kind="suspendUser" target={target} onClose={onClose} onDone={vi.fn()} />,
      repo,
    );
    await userEvent.type(screen.getByLabelText('정지 사유 *'), 'x');
    await userEvent.click(screen.getByRole('button', { name: '정지하기' }));
    await userEvent.keyboard('{Escape}');
    expect(screen.getByRole('button', { name: '취소' })).toBeDisabled();
    expect(onClose).not.toHaveBeenCalled();
    d.resolve();
    await waitFor(() => expect(screen.getByRole('button', { name: '취소' })).toBeEnabled());
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(repo.suspendUser).toHaveBeenCalledTimes(1);
  });

  it('서버 오류 문구를 보인다', async () => {
    const repo = new FakeAdminRepository();
    repo.suspendUser.mockRejectedValue(
      new ApiError(400, 'USER_ALREADY_SUSPENDED', '이미 정지된 회원입니다.'),
    );
    const onDone = vi.fn();
    renderAdmin(
      <SanctionSheet kind="suspendUser" target={target} onClose={vi.fn()} onDone={onDone} />,
      repo,
    );
    await userEvent.type(screen.getByLabelText('정지 사유 *'), 'x');
    await userEvent.click(screen.getByRole('button', { name: '정지하기' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('이미 정지된 회원입니다.');
    expect(onDone).not.toHaveBeenCalled();
  });

  it('취소·Esc로 닫는다', async () => {
    const onClose = vi.fn();
    renderAdmin(
      <SanctionSheet kind="suspendStore" target={target} onClose={onClose} onDone={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole('button', { name: '취소' }));
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});

describe('PointGrantSheet (M4)', () => {
  const grantTarget = { id: 'u1', name: '박고객', email: 'c@x', balance: 2300 };

  it('버튼 문구에 금액, 지급 후 잔액을 보인다', async () => {
    renderAdmin(<PointGrantSheet target={grantTarget} onClose={vi.fn()} onDone={vi.fn()} />);
    // 현재 잔액과 (금액 입력 전) 지급 후 잔액이 같다
    expect(screen.getAllByText('2,300P')).toHaveLength(2);
    expect(screen.getByRole('button', { name: '지급' })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('지급 포인트 * (1 이상)'), '1,000');
    expect(screen.getByRole('button', { name: '1,000P 지급' })).toBeInTheDocument();
    expect(screen.getByText('3,300P')).toBeInTheDocument();
  });

  it('금액이 1 미만이면 보내지 않는다', async () => {
    const { repo } = renderAdmin(
      <PointGrantSheet target={grantTarget} onClose={vi.fn()} onDone={vi.fn()} />,
    );
    await userEvent.type(screen.getByLabelText('지급 포인트 * (1 이상)'), '0');
    await userEvent.type(screen.getByLabelText('지급 사유 *'), '보상');
    await userEvent.click(screen.getByRole('button', { name: '지급' }));
    expect(screen.getByRole('alert')).toHaveTextContent('지급 포인트는 1 이상이어야 합니다.');
    expect(repo.grantPoints).not.toHaveBeenCalled();
  });

  it('지급하면 onDone(지급 후 잔액)', async () => {
    const onDone = vi.fn();
    const { repo } = renderAdmin(
      <PointGrantSheet target={grantTarget} onClose={vi.fn()} onDone={onDone} />,
    );
    await userEvent.type(screen.getByLabelText('지급 포인트 * (1 이상)'), '1000');
    await userEvent.type(screen.getByLabelText('지급 사유 *'), ' 배송 지연 보상 ');
    await userEvent.click(screen.getByRole('button', { name: '1,000P 지급' }));
    expect(repo.grantPoints).toHaveBeenCalledWith('u1', 1000, '배송 지연 보상');
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(3300));
  });
});
