import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { routes } from '@/app/router/routes';
import type { User } from '@/features/auth';
import { ApiError } from '@/shared/api/error';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';
import { makePointPage, recentLogs } from '../../features/auth/fakes/points';
import { customerUser } from '../../features/auth/fakes/users';

function renderMy(fakes: AuthFakes = signedInFakes(customerUser)) {
  return renderRoutesWithAuth(routes, { initialEntries: ['/me'], fakes });
}

function withRecentPoints(user: User = customerUser): AuthFakes {
  const fakes = signedInFakes(user);
  fakes.account.findPoints.mockResolvedValue(
    makePointPage(recentLogs(), { balance: 1240, size: 3, total: 3 }),
  );
  return fakes;
}

describe('MyPage (C6·C10)', () => {
  it('「마이」 heading, 이름·이메일, 포인트 1,240P(포인트 응답 잔액), 탭 「마이」 현재', async () => {
    const fakes = withRecentPoints();
    renderMy(fakes);
    expect(await screen.findByRole('heading', { level: 1, name: '마이' })).toBeInTheDocument();
    expect(screen.getByText('고객')).toBeInTheDocument();
    expect(screen.getByText('customer@test.com')).toBeInTheDocument();
    expect(await screen.findByText('1,240P')).toBeInTheDocument();
    expect(fakes.account.findPoints.mock.calls[0]?.[0]).toEqual({ page: 0, size: 3 });
    const nav = screen.getByRole('navigation', { name: '고객 메뉴' });
    expect(within(nav).getByRole('link', { name: '마이' })).toHaveAttribute('aria-current', 'page');
  });

  it('「프로필 변경」·「비밀번호 변경」 행은 C8·C9 링크이고 누르면 state.from이 /me', async () => {
    const { router } = renderMy(withRecentPoints());
    const profile = await screen.findByRole('link', { name: /프로필 변경/ });
    expect(profile).toHaveAttribute('href', '/account/profile');
    expect(screen.getByRole('link', { name: /비밀번호 변경/ })).toHaveAttribute(
      'href',
      '/account/password',
    );
    await userEvent.click(profile);
    await waitFor(() => expect(router.state.location.pathname).toBe('/account/profile'));
    expect(router.state.location.state).toEqual({ from: '/me' });
  });

  it('최근 포인트 내역 3행: 종류·날짜·금액', async () => {
    renderMy(withRecentPoints());
    expect(await screen.findByText('+115P')).toBeInTheDocument();
    expect(screen.getByText('적립')).toBeInTheDocument();
    expect(screen.getByText('11/07')).toBeInTheDocument();
    expect(screen.getByText('사용')).toBeInTheDocument();
    expect(screen.getByText('−500P')).toBeInTheDocument();
    expect(screen.getByText('지급')).toBeInTheDocument();
    expect(screen.getByText('최근 포인트 내역')).toBeInTheDocument();
  });

  it('「전체 보기」는 /me/points, 「회원 탈퇴」는 /me/withdraw', async () => {
    renderMy(withRecentPoints());
    expect(await screen.findByRole('link', { name: '전체 보기' })).toHaveAttribute(
      'href',
      '/me/points',
    );
    expect(screen.getByRole('link', { name: '회원 탈퇴' })).toHaveAttribute('href', '/me/withdraw');
  });

  it('포인트 불러오기 실패: 상자는 사용자 point, 내역 자리에 임시 문구와 「다시 시도」', async () => {
    const fakes = signedInFakes({ ...customerUser, point: 500 });
    fakes.account.findPoints.mockRejectedValueOnce(new ApiError(500, 'INTERNAL_ERROR', '서버'));
    renderMy(fakes);
    expect(
      await screen.findByText('불러오지 못했어요. 잠시 후 다시 시도해 주세요.'),
    ).toBeInTheDocument();
    expect(screen.getByText('500P')).toBeInTheDocument();
    fakes.account.findPoints.mockResolvedValue(makePointPage(recentLogs(), { total: 3 }));
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByText('+115P')).toBeInTheDocument();
  });

  it('포인트 내역 0건이면 「포인트 내역이 없어요」', async () => {
    renderMy(signedInFakes(customerUser));
    expect(await screen.findByText('포인트 내역이 없어요')).toBeInTheDocument();
  });

  it('「로그아웃」은 .dim 안 확인 시트(설명 한 줄 포함)를 열고 「취소」로 닫는다', async () => {
    renderMy(withRecentPoints());
    await userEvent.click(await screen.findByRole('button', { name: /로그아웃/ }));
    const sheet = await screen.findByRole('alertdialog', { name: '로그아웃할까요?' });
    await waitFor(() => expect(within(sheet).getByRole('button', { name: '취소' })).toHaveFocus());
    expect(sheet.closest('.dim')).not.toBeNull();
    expect(
      within(sheet).getByText('진행 중인 예약은 그대로 남아요. 다시 로그인하면 볼 수 있어요.'),
    ).toBeInTheDocument();
    // 본문은 DOM에 남되 숨겨진다(이전 단언 「전체 보기 링크가 없다」를 의도에 맞게 교체)
    const body = document.querySelector('.app > .body');
    expect(body).toHaveAttribute('hidden');
    expect(screen.queryByRole('link', { name: '전체 보기' })).not.toBeInTheDocument();
    await userEvent.click(within(sheet).getByRole('button', { name: '취소' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(screen.getByRole('link', { name: '전체 보기' })).toBeInTheDocument();
  });

  it('시트가 열려 있는 동안 .body는 hidden으로 남고 .dim이 .app 직계 자식이며, 닫으면 hidden이 풀린다', async () => {
    renderMy(withRecentPoints());
    await userEvent.click(await screen.findByRole('button', { name: /로그아웃/ }));
    const sheet = await screen.findByRole('alertdialog', { name: '로그아웃할까요?' });
    const app = document.querySelector('.app') as HTMLElement;
    const dim = sheet.closest('.dim');
    expect(dim?.parentElement).toBe(app);
    expect(Array.from(app.children).indexOf(dim as Element)).toBeGreaterThan(
      Array.from(app.children).indexOf(app.querySelector(':scope > .body') as Element),
    );
    expect(app.querySelector(':scope > .body')).toHaveAttribute('hidden');
    await userEvent.click(within(sheet).getByRole('button', { name: '취소' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(app.querySelector(':scope > .body')).not.toHaveAttribute('hidden');
  });

  it('시트를 닫은 뒤 .body는 같은 노드이고 scrollTop이 유지된다', async () => {
    renderMy(withRecentPoints());
    const logout = await screen.findByRole('button', { name: /로그아웃/ });
    const body = document.querySelector('.app > .body') as HTMLElement;
    body.scrollTop = 120;
    await userEvent.click(logout);
    const sheet = await screen.findByRole('alertdialog', { name: '로그아웃할까요?' });
    await userEvent.click(within(sheet).getByRole('button', { name: '취소' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(document.querySelector('.app > .body')).toBe(body);
    expect(body.scrollTop).toBe(120);
  });

  it('시트 안 Tab·Shift+Tab은 시트 안에서만 돈다', async () => {
    renderMy(withRecentPoints());
    await userEvent.click(await screen.findByRole('button', { name: /로그아웃/ }));
    const sheet = await screen.findByRole('alertdialog', { name: '로그아웃할까요?' });
    const cancel = within(sheet).getByRole('button', { name: '취소' });
    const confirm = within(sheet).getByRole('button', { name: '로그아웃' });
    await waitFor(() => expect(cancel).toHaveFocus());
    await userEvent.tab();
    expect(confirm).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(cancel).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(confirm).toHaveFocus();
  });

  it('로그아웃 시트를 Escape로 닫으면 포커스가 「로그아웃」 버튼으로 돌아온다', async () => {
    renderMy(withRecentPoints());
    await userEvent.click(await screen.findByRole('button', { name: /로그아웃/ }));
    const sheet = await screen.findByRole('alertdialog', { name: '로그아웃할까요?' });
    await waitFor(() => expect(within(sheet).getByRole('button', { name: '취소' })).toHaveFocus());
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole('button', { name: /로그아웃/ })).toHaveFocus());
  });

  it('로그아웃 시트를 「취소」로 닫아도 포커스가 「로그아웃」 버튼으로 돌아온다', async () => {
    renderMy(withRecentPoints());
    await userEvent.click(await screen.findByRole('button', { name: /로그아웃/ }));
    const sheet = await screen.findByRole('alertdialog', { name: '로그아웃할까요?' });
    await userEvent.click(within(sheet).getByRole('button', { name: '취소' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole('button', { name: /로그아웃/ })).toHaveFocus());
  });

  it('로그아웃을 확정하면 auth.logout을 부르고 /(상단 「로그인」 보임)로 간다', async () => {
    const fakes = withRecentPoints();
    const { router } = renderMy(fakes);
    await userEvent.click(await screen.findByRole('button', { name: /로그아웃/ }));
    const sheet = await screen.findByRole('alertdialog', { name: '로그아웃할까요?' });
    await userEvent.click(within(sheet).getByRole('button', { name: '로그아웃' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(fakes.auth.logout).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole('link', { name: '로그인' })).toBeInTheDocument();
  });

  it('/me 비로그인 진입 → /login 안내 「예약 내역을 보려면 로그인하세요.」, 고객 로그인 → /me', async () => {
    const fakes = anonymousFakes();
    fakes.auth.findMe.mockResolvedValue(customerUser);
    const { router } = renderMy(fakes);
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(await screen.findByText('예약 내역을 보려면 로그인하세요.')).toBeInTheDocument();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('이메일'), 'customer@test.com');
    await user.type(screen.getByLabelText('비밀번호'), 'pw123456');
    await user.click(screen.getByRole('button', { name: '로그인' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/me'));
    expect(await screen.findByRole('heading', { level: 1, name: '마이' })).toBeInTheDocument();
  });
});
