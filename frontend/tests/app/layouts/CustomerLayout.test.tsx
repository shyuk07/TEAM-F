import { screen, waitFor } from '@testing-library/react';
import type { RouteObject } from 'react-router';
import { CustomerLayout } from '@/app/layouts/CustomerLayout';
import { TAB_BAR_HANDLE } from '@/app/router/handle';
import { ApiError } from '@/shared/api/error';
import { customerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';

function renderLayout(opts: { tabBar?: boolean; fakes?: AuthFakes } = {}) {
  const routes: RouteObject[] = [
    { path: '/login', element: <p>로그인 화면</p> },
    {
      element: <CustomerLayout />,
      children: [
        {
          path: '/',
          element: <p>홈 본문</p>,
          handle: opts.tabBar === false ? {} : TAB_BAR_HANDLE,
        },
      ],
    },
  ];
  return renderRoutesWithAuth(routes, {
    initialEntries: ['/'],
    fakes: opts.fakes ?? anonymousFakes(),
  });
}

describe('CustomerLayout', () => {
  it('anonymous여도 가드 없이 홈이 보이고 /login으로 가지 않는다', async () => {
    const { router } = renderLayout();
    expect(await screen.findByText('홈 본문')).toBeInTheDocument();
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(screen.queryByText('로그인 화면')).not.toBeInTheDocument();
  });

  it('세션 확인이 error여도 홈이 보인다', async () => {
    const fakes = signedInFakes(customerUser);
    fakes.auth.findMe.mockRejectedValue(new ApiError(500, 'INTERNAL_ERROR', 'x'));
    renderLayout({ fakes });
    expect(await screen.findByText('홈 본문')).toBeInTheDocument();
    await waitFor(() => expect(fakes.auth.findMe).toHaveBeenCalled());
    expect(screen.getByText('홈 본문')).toBeInTheDocument();
  });

  it('탭 핸들이 있는 라우트에는 탭 바가 Outlet 뒤에 있다', async () => {
    renderLayout();
    const body = await screen.findByText('홈 본문');
    const tabs = document.querySelector('.tabs');
    expect(tabs).not.toBeNull();
    expect(body.parentElement?.lastElementChild).toBe(tabs);
  });

  it('탭 핸들이 없는 라우트에는 탭 바가 없다', async () => {
    renderLayout({ tabBar: false });
    await screen.findByText('홈 본문');
    expect(document.querySelector('.tabs')).toBeNull();
  });

  it('.app 프레임이 있다', async () => {
    const { container } = renderLayout();
    await screen.findByText('홈 본문');
    expect(container.querySelector('.app')).not.toBeNull();
    expect(screen.getByText('홈 본문').parentElement).toHaveClass('app');
  });
});
