import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, type RouteObject } from 'react-router';
import { useAuth } from '@/features/auth';
import { ApiError } from '@/shared/api/error';
import { OwnerAccountButton } from '@/widgets/owner-nav';
import { deferred } from '../../../features/auth/fakes/deferred';
import { adminUser, ownerUser } from '../../../features/auth/fakes/users';
import { signedInFakes, type AuthFakes } from '../../../support/authFakes';
import { renderRoutesWithAuth, renderWithAuth } from '../../../support/renderWithAuth';

function AuthProbe() {
  const { state } = useAuth();
  return (
    <output data-testid="auth">
      {state.status === 'anonymous' ? `anonymous:${state.cause}` : state.status}
    </output>
  );
}

async function renderMenu(fakes: AuthFakes = signedInFakes()) {
  const result = renderWithAuth(
    <MemoryRouter initialEntries={['/owner/store']}>
      <div className="app">
        <OwnerAccountButton />
        <AuthProbe />
      </div>
    </MemoryRouter>,
    { fakes },
  );
  await waitFor(() => expect(screen.getByTestId('auth')).toHaveTextContent('authenticated'));
  return {
    ...result,
    user: userEvent.setup(),
    button: screen.getByRole('button', { name: '계정' }),
  };
}

const menu = () => screen.getByRole('dialog', { name: '계정 메뉴' });

async function openLogoutConfirm(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: '계정' }));
  await user.click(within(menu()).getByRole('button', { name: /^로그아웃/ }));
  return screen.getByRole('alertdialog');
}

describe('OwnerAccountMenu (O8·C10)', () => {
  it('처음에는 aria-haspopup="dialog", aria-expanded="false"이고 메뉴가 없다', async () => {
    const { button } = await renderMenu();
    expect(button).toHaveAttribute('aria-haspopup', 'dialog');
    expect(button).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('클릭하면 이름·이메일·역할과 「로그아웃」 행이 있는 대화상자가 열린다', async () => {
    const { user, button } = await renderMenu();
    await user.click(button);
    expect(button).toHaveAttribute('aria-expanded', 'true');
    const dialog = menu();
    expect(within(dialog).getByText('망원베이커리')).toBeInTheDocument();
    expect(within(dialog).getByText('owner@test.com · 상점주')).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: /^로그아웃/ })).toBeInTheDocument();
  });

  it('대화상자는 .app 프레임 안에 있다', async () => {
    const { user, button, container } = await renderMenu();
    await user.click(button);
    expect(menu().closest('.app')).toBe(container.querySelector('.app'));
  });

  it('name이 null이면 제목이 이메일이다', async () => {
    const { user, button } = await renderMenu(signedInFakes({ ...ownerUser, name: null }));
    await user.click(button);
    expect(within(menu()).getByText('owner@test.com')).toBeInTheDocument();
  });

  it('Esc로 닫히고 포커스가 「계정」 버튼으로 돌아간다', async () => {
    const { user, button } = await renderMenu();
    await user.click(button);
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(button).toHaveFocus();
  });

  it('딤 영역을 누르면 닫힌다', async () => {
    const { user, button } = await renderMenu();
    await user.click(button);
    const dim = menu().parentElement;
    expect(dim).not.toBeNull();
    await user.click(dim as HTMLElement);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('「로그아웃」 행을 누르면 「로그아웃할까요?」 확인 시트가 열린다', async () => {
    const { user } = await renderMenu();
    const confirm = await openLogoutConfirm(user);
    expect(within(confirm).getByText('로그아웃할까요?')).toBeInTheDocument();
    expect(within(confirm).getByRole('button', { name: '로그아웃' })).toBeInTheDocument();
    expect(within(confirm).getByRole('button', { name: '취소' })).toBeInTheDocument();
  });

  it('「취소」는 시트를 닫고 logout을 부르지 않는다', async () => {
    const { user, fakes } = await renderMenu();
    const confirm = await openLogoutConfirm(user);
    await user.click(within(confirm).getByRole('button', { name: '취소' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(fakes.auth.logout).not.toHaveBeenCalled();
  });

  it('확인하면 logout·session.clear가 1회씩이고 상태가 anonymous(loggedOut)가 된다', async () => {
    const { user, fakes } = await renderMenu();
    const confirm = await openLogoutConfirm(user);
    await user.click(within(confirm).getByRole('button', { name: '로그아웃' }));
    await waitFor(() =>
      expect(screen.getByTestId('auth')).toHaveTextContent('anonymous:loggedOut'),
    );
    expect(fakes.auth.logout).toHaveBeenCalledTimes(1);
    expect(fakes.session.clear).toHaveBeenCalledTimes(1);
  });

  it('확인 중에는 「처리 중…」·aria-disabled이고 연타해도 logout은 1회다', async () => {
    const fakes = signedInFakes();
    const d = deferred<void>();
    const { user } = await renderMenu(fakes);
    fakes.auth.logout.mockReturnValue(d.promise);
    const confirm = await openLogoutConfirm(user);
    await user.click(within(confirm).getByRole('button', { name: '로그아웃' }));
    const busy = await within(screen.getByRole('alertdialog')).findByRole('button', {
      name: '처리 중…',
    });
    expect(busy).toHaveAttribute('aria-disabled', 'true');
    await user.click(busy);
    expect(fakes.auth.logout).toHaveBeenCalledTimes(1);
  });

  it('서버가 401 TOKEN_REVOKED로 거절해도 session.clear를 부르고 시트가 닫힌다', async () => {
    const fakes = signedInFakes();
    const { user } = await renderMenu(fakes);
    fakes.auth.logout.mockRejectedValue(new ApiError(401, 'TOKEN_REVOKED', 'x'));
    const confirm = await openLogoutConfirm(user);
    await user.click(within(confirm).getByRole('button', { name: '로그아웃' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(fakes.session.clear).toHaveBeenCalled();
  });
});

function OwnerScreen() {
  return (
    <div className="app">
      <OwnerAccountButton />
      <AuthProbe />
    </div>
  );
}

const menuRoutes: RouteObject[] = [
  { path: '/owner/offers', element: <OwnerScreen /> },
  { path: '/owner/store', element: <OwnerScreen /> },
  { path: '/account/profile', element: <p>프로필 화면</p> },
  { path: '/account/password', element: <p>비밀번호 화면</p> },
];

async function renderMenuInRoutes(fakes: AuthFakes = signedInFakes(), path = '/owner/store') {
  const result = renderRoutesWithAuth(menuRoutes, { initialEntries: [path], fakes });
  await waitFor(() => expect(screen.getByTestId('auth')).toHaveTextContent('authenticated'));
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: '계정' }));
  return { ...result, user };
}

const profileRow = () => within(menu()).getByRole('link', { name: /^내 정보 \(전화번호\)/ });
const passwordRow = () => within(menu()).getByRole('link', { name: /^비밀번호 변경/ });

describe('OwnerAccountMenu C8·C9 행 (auth-account D-23)', () => {
  it('메뉴 행 순서는 「내 정보 (전화번호)」, 「비밀번호 변경」, 「로그아웃」이다', async () => {
    await renderMenuInRoutes();
    const list = menu().querySelector('.list');
    expect(list).not.toBeNull();
    const rows = Array.from((list as HTMLElement).children).map((el) => el.textContent ?? '');
    expect(rows).toHaveLength(3);
    expect(rows[0]).toMatch(/^내 정보 \(전화번호\)/);
    expect(rows[1]).toMatch(/^비밀번호 변경/);
    expect(rows[2]).toMatch(/^로그아웃/);
  });

  it('「내 정보 (전화번호)」는 /account/profile, 「비밀번호 변경」은 /account/password 링크다', async () => {
    await renderMenuInRoutes();
    expect(profileRow()).toHaveAttribute('href', '/account/profile');
    expect(passwordRow()).toHaveAttribute('href', '/account/password');
  });

  it('/owner/offers?x=1에서 「내 정보 (전화번호)」를 누르면 /account/profile로 가고 from을 넘기며 시트가 없다', async () => {
    const { router, user } = await renderMenuInRoutes(signedInFakes(), '/owner/offers?x=1');
    await user.click(profileRow());
    await waitFor(() => expect(router.state.location.pathname).toBe('/account/profile'));
    expect(router.state.location.state).toEqual({ from: '/owner/offers?x=1' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('OWNER면 매장 탭 안내가 있고 ADMIN이면 없다', async () => {
    const owner = await renderMenuInRoutes(signedInFakes(ownerUser));
    expect(within(menu()).getByText('상점 정보·폐점은 매장 탭(O4)에 있어요.')).toBeInTheDocument();
    owner.unmount();

    await renderMenuInRoutes(signedInFakes(adminUser));
    expect(
      within(menu()).queryByText('상점 정보·폐점은 매장 탭(O4)에 있어요.'),
    ).not.toBeInTheDocument();
  });

  it('열면 포커스가 「내 정보 (전화번호)」 링크에 있다', async () => {
    await renderMenuInRoutes();
    expect(profileRow()).toHaveFocus();
  });

  it('시트 안 Tab 순환이 링크 2개와 「로그아웃」 버튼 사이에서 돈다', async () => {
    const { user } = await renderMenuInRoutes();
    const logoutRow = within(menu()).getByRole('button', { name: /^로그아웃/ });
    logoutRow.focus();
    await user.tab();
    expect(profileRow()).toHaveFocus();
    await user.tab();
    expect(passwordRow()).toHaveFocus();
    await user.tab();
    expect(logoutRow).toHaveFocus();
    await user.tab({ shift: true });
    expect(passwordRow()).toHaveFocus();
  });
});

describe('OwnerAccountMenu 포커스 트랩', () => {
  it('로그아웃 확인 시트에서 마지막 요소 Tab은 첫 요소로, 첫 요소 Shift+Tab은 마지막으로 간다', async () => {
    const { user } = await renderMenu();
    const sheet = await openLogoutConfirm(user);
    const buttons = within(sheet).getAllByRole('button');
    const first = buttons[0];
    const last = buttons[buttons.length - 1];
    last.focus();
    await user.tab();
    expect(first).toHaveFocus();
    await user.tab({ shift: true });
    expect(last).toHaveFocus();
  });
});
