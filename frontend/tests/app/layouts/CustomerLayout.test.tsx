import { screen, waitFor } from '@testing-library/react';
import { type RouteObject } from 'react-router';
import { CustomerLayout } from '@/app/layouts/CustomerLayout';
import type { User } from '@/features/auth';
import { deferred } from '../../features/auth/fakes/deferred';
import { adminUser, customerUser, ownerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';

function renderGuard(fakes: AuthFakes, path = '/me/reservations') {
  const routes: RouteObject[] = [
    { path: '/login', element: <p>로그인 화면</p> },
    { path: '/', element: <p>홈 화면</p> },
    {
      element: <CustomerLayout />,
      children: [{ path: '/me/reservations', element: <p>본문</p> }],
    },
  ];
  return renderRoutesWithAuth(routes, { initialEntries: [path], fakes });
}

describe('CustomerLayout 인증 가드', () => {
  it('CUSTOMER면 본문(Outlet)을 그린다', async () => {
    renderGuard(signedInFakes(customerUser));
    expect(await screen.findByText('본문')).toBeInTheDocument();
  });

  it('세션 확인 중에는 본문이 없고 aria-busy 프레임만 있다', () => {
    const fakes = signedInFakes(customerUser);
    fakes.auth.findMe.mockReturnValue(deferred<User>().promise);
    renderGuard(fakes);
    expect(screen.queryByText('본문')).not.toBeInTheDocument();
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
  });

  it('비로그인이면 /login으로 이동하고 state.from이 원래 경로(쿼리 포함)다', async () => {
    const { router } = renderGuard(anonymousFakes(), '/me/reservations?tab=past');
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/me/reservations?tab=past' });
  });

  it.each([
    ['OWNER', ownerUser],
    ['ADMIN', adminUser],
  ])('%s면 /로 이동한다', async (_label, user) => {
    const { router } = renderGuard(signedInFakes(user));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(screen.queryByText('본문')).not.toBeInTheDocument();
  });
});
