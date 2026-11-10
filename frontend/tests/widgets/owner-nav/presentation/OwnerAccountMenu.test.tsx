import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { useAuth } from '@/features/auth';
import { ApiError } from '@/shared/api/error';
import { OwnerAccountButton } from '@/widgets/owner-nav';
import { deferred } from '../../../features/auth/fakes/deferred';
import { ownerUser } from '../../../features/auth/fakes/users';
import { signedInFakes, type AuthFakes } from '../../../support/authFakes';
import { renderWithAuth } from '../../../support/renderWithAuth';

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
