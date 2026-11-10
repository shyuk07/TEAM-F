import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RouteObject } from 'react-router';
import { AccountLayout } from '@/app/layouts/AccountLayout';
import { useAuth, type User } from '@/features/auth';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../features/auth/fakes/deferred';
import { adminUser, customerUser, ownerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';

function LogoutTrigger() {
  const { logout } = useAuth();
  return (
    <button type="button" onClick={() => void logout()}>
      테스트 로그아웃
    </button>
  );
}

function renderGuard(fakes: AuthFakes, path = '/account/profile') {
  const routes: RouteObject[] = [
    { path: '/login', element: <p>로그인 화면</p> },
    { path: '/', element: <p>홈 화면</p> },
    {
      element: <AccountLayout />,
      children: [
        {
          path: '/account/profile',
          element: (
            <>
              <p>본문</p>
              <LogoutTrigger />
            </>
          ),
        },
      ],
    },
  ];
  return renderRoutesWithAuth(routes, { initialEntries: [path], fakes });
}

describe('AccountLayout (역할 무관 로그인 필요 가드)', () => {
  it('세션 확인 중에는 본문 없이 aria-busy 프레임만 있다', () => {
    const fakes = signedInFakes();
    fakes.auth.findMe.mockReturnValue(deferred<User>().promise);
    renderGuard(fakes);
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(screen.queryByText('본문')).not.toBeInTheDocument();
  });

  it('anonymous(other)면 /login으로 가고 state.from이 /account/profile이다', async () => {
    const { router } = renderGuard(anonymousFakes());
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/account/profile' });
  });

  it('쿼리가 있는 경로면 from에 쿼리가 포함된다', async () => {
    const { router } = renderGuard(anonymousFakes(), '/account/profile?x=1');
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/account/profile?x=1' });
  });

  it('직접 로그아웃하면 /login으로 가고 state는 null이다', async () => {
    const { router } = renderGuard(signedInFakes());
    await userEvent.click(await screen.findByRole('button', { name: '테스트 로그아웃' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toBeNull();
  });

  it.each<[string, User]>([
    ['OWNER', ownerUser],
    ['CUSTOMER', customerUser],
    ['ADMIN', adminUser],
  ])('%s면 본문이 보인다', async (_name, user) => {
    const { router } = renderGuard(signedInFakes(user));
    expect(await screen.findByText('본문')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/account/profile');
  });

  it('error면 오류 문구와 「다시 시도」가 있고 누르면 재시도 성공 뒤 본문이 보인다', async () => {
    const fakes = signedInFakes();
    fakes.auth.findMe.mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', '네트워크 문구'));
    renderGuard(fakes);
    expect(await screen.findByRole('alert')).toHaveTextContent('네트워크 문구');
    expect(screen.queryByText('본문')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByText('본문')).toBeInTheDocument();
  });
});
