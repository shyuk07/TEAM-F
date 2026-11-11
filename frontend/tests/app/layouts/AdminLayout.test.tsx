import { screen, waitFor } from '@testing-library/react';
import { type RouteObject } from 'react-router';
import { AdminLayout } from '@/app/layouts/AdminLayout';
import { adminUser, customerUser, ownerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';

function renderGuard(fakes: AuthFakes, tabBar = true) {
  const routes: RouteObject[] = [
    { path: '/', element: <p>홈</p> },
    { path: '/login', element: <p>로그인 화면</p> },
    {
      element: <AdminLayout />,
      children: [
        { path: '/admin/users', element: <p>회원 본문</p>, handle: tabBar ? { tabBar: true } : {} },
      ],
    },
  ];
  return renderRoutesWithAuth(routes, { initialEntries: ['/admin/users'], fakes });
}

describe('AdminLayout', () => {
  it('관리자는 통과: 상단 바(관리자·nav·계정)와 하단 탭 바', async () => {
    renderGuard(signedInFakes(adminUser));
    expect(await screen.findByText('회원 본문')).toBeInTheDocument();
    expect(screen.getByText('관리자', { selector: '.logo' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '계정' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '관리자 메뉴' })).toBeInTheDocument();
    const current = screen.getAllByRole('link', { current: 'page' });
    expect(current.every((a) => a.textContent === '회원')).toBe(true);
  });

  it('하위 화면에는 하단 탭 바가 없다', async () => {
    renderGuard(signedInFakes(adminUser), false);
    await screen.findByText('회원 본문');
    expect(screen.queryByRole('navigation', { name: '관리자 메뉴' })).not.toBeInTheDocument();
  });

  it.each([
    ['상점주', ownerUser],
    ['고객', customerUser],
  ])('%s이면 /로 보낸다', async (_n, user) => {
    const { router } = renderGuard(signedInFakes(user));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });

  it('비로그인이면 로그인으로, 돌아올 경로를 담는다', async () => {
    const { router } = renderGuard(anonymousFakes());
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/admin/users' });
  });
});
