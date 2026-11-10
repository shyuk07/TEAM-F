import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MembersPanel, UserDetailPanel, type MemberSearch } from '@/features/admin';
import {
  FakeAdminRepository,
  customer,
  customerDetail,
  page,
  pendingOwner,
} from '../fakes/fakeAdminRepository.fake';
import { renderAdmin } from '../fakes/renderAdmin';

const start: MemberSearch = { filter: 'all', email: '', page: 1 };

describe('MembersPanel (M3 목록)', () => {
  it('회원 행: 이름·이메일·역할 코드·상태 코드, 선택한 행 표시, 페이지 요약', async () => {
    const repo = new FakeAdminRepository();
    repo.listUsers.mockResolvedValue(page([customer, pendingOwner], 134));
    renderAdmin(
      <MembersPanel
        search={start}
        onSearchChange={vi.fn()}
        selectedId={customer.id}
        rowHref={(id) => `/admin/users/${id}`}
        version={0}
      />,
      repo,
    );
    const row = await screen.findByRole('link', { name: /박고객/ });
    expect(row).toHaveAttribute('href', `/admin/users/${customer.id}`);
    expect(row).toHaveAttribute('aria-current', 'true');
    expect(within(row).getByText('CUSTOMER')).toBeInTheDocument();
    expect(within(row).getByText('APPROVED')).toBeInTheDocument();
    expect(screen.getByText('1–20 / 134명')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '이전' })).toBeDisabled();
  });

  it('칩을 누르면 1페이지로 필터를 바꾼다', async () => {
    const onSearchChange = vi.fn();
    renderAdmin(
      <MembersPanel
        search={{ filter: 'all', email: '', page: 3 }}
        onSearchChange={onSearchChange}
        selectedId={null}
        rowHref={(id) => id}
        version={0}
      />,
    );
    expect(screen.getByRole('button', { name: '전체' })).toHaveAttribute('aria-pressed', 'true');
    await userEvent.click(screen.getByRole('button', { name: '정지' }));
    expect(onSearchChange).toHaveBeenCalledWith({ filter: 'suspended', email: '', page: 1 });
  });

  it('2페이지 이상이 비면 「이전」으로 돌아갈 수 있다', async () => {
    const onSearchChange = vi.fn();
    const repo = new FakeAdminRepository();
    repo.listUsers.mockResolvedValue(page([], 20, 2));
    renderAdmin(
      <MembersPanel
        search={{ filter: 'all', email: '', page: 2 }}
        onSearchChange={onSearchChange}
        selectedId={null}
        rowHref={(id) => id}
        version={0}
      />,
      repo,
    );
    await userEvent.click(await screen.findByRole('button', { name: '이전' }));
    expect(onSearchChange).toHaveBeenCalledWith({ filter: 'all', email: '', page: 1 });
  });

  it('주소의 검색어가 바뀌면 입력칸도 바뀐다', async () => {
    const props = {
      onSearchChange: vi.fn(),
      selectedId: null,
      rowHref: (id: string) => id,
      version: 0,
    };
    const { rerender } = renderAdmin(
      <MembersPanel search={{ filter: 'all', email: 'a@x', page: 1 }} {...props} />,
    );
    expect(screen.getByRole('searchbox')).toHaveValue('a@x');
    rerender(<MembersPanel search={{ filter: 'all', email: '', page: 1 }} {...props} />);
    expect(screen.getByRole('searchbox')).toHaveValue('');
  });

  it('필터대로 목록을 요청하고, 없으면 빈 상태', async () => {
    const { repo } = renderAdmin(
      <MembersPanel
        search={{ filter: 'withdrawn', email: 'x@', page: 2 }}
        onSearchChange={vi.fn()}
        selectedId={null}
        rowHref={(id) => id}
        version={0}
      />,
    );
    expect(await screen.findByText('조건에 맞는 회원이 없어요')).toBeInTheDocument();
    expect(repo.listUsers).toHaveBeenCalledWith(
      { status: 'WITHDRAWN', email: 'x@', page: 2, size: 20 },
      expect.any(AbortSignal),
    );
  });
});

describe('UserDetailPanel (M3 상세)', () => {
  it('정보·가린 전화번호·포인트·최근 내역(코드 병기)', async () => {
    const { repo } = renderAdmin(<UserDetailPanel userId={customer.id} onChanged={vi.fn()} />);
    expect(await screen.findByText('customer3@example.com · 010-****-5678')).toBeInTheDocument();
    expect(screen.getByText('2,300P')).toBeInTheDocument();
    expect(screen.getByText('EARN')).toBeInTheDocument();
    expect(screen.getByText('+1,000P')).toBeInTheDocument();
    expect(repo.findUserPoints).toHaveBeenCalledWith(customer.id, 1, 5, expect.any(AbortSignal));
  });

  it('포인트 지급 후 상세·목록을 다시 불러온다', async () => {
    const onChanged = vi.fn();
    const { repo } = renderAdmin(<UserDetailPanel userId={customer.id} onChanged={onChanged} />);
    await userEvent.click(await screen.findByRole('button', { name: '포인트 지급' }));
    const dialog = screen.getByRole('dialog', { name: '포인트 지급' });
    await userEvent.type(within(dialog).getByLabelText('지급 포인트 * (1 이상)'), '1000');
    await userEvent.type(within(dialog).getByLabelText('지급 사유 *'), '보상');
    await userEvent.click(within(dialog).getByRole('button', { name: '1,000P 지급' }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(repo.findUser).toHaveBeenCalledTimes(2);
  });

  it('강제 탈퇴 후 취소한 예약 수를 보인다', async () => {
    const repo = new FakeAdminRepository();
    repo.withdrawUser.mockResolvedValue({ cancelledReservationCount: 2 });
    renderAdmin(<UserDetailPanel userId={customer.id} onChanged={vi.fn()} />, repo);
    await userEvent.click(await screen.findByRole('button', { name: '강제 탈퇴' }));
    const dialog = screen.getByRole('dialog', { name: '강제 탈퇴' });
    await userEvent.type(within(dialog).getByLabelText('탈퇴 사유 *'), '사기');
    await userEvent.click(within(dialog).getByRole('button', { name: '탈퇴시키기' }));
    expect(await screen.findByRole('status')).toHaveTextContent('취소한 예약 2건');
  });

  it('탈퇴 회원은 버튼이 없다', async () => {
    const repo = new FakeAdminRepository();
    repo.findUser.mockResolvedValue({ ...customerDetail, status: 'WITHDRAWN' });
    renderAdmin(<UserDetailPanel userId={customer.id} onChanged={vi.fn()} />, repo);
    expect(await screen.findByText('WITHDRAWN')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '포인트 지급' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '강제 탈퇴' })).not.toBeInTheDocument();
  });
});
