import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RouteObject } from 'react-router';
import { useAuth } from '@/features/auth';
import type { User } from '@/features/auth';
import { CustomerTabBar } from '@/widgets/customer-nav';
import { deferred } from '../../../features/auth/fakes/deferred';
import { customerUser } from '../../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../../support/authFakes';
import { renderRoutesWithAuth } from '../../../support/renderWithAuth';

function AuthProbe() {
  const { state } = useAuth();
  return <output data-testid="auth">{state.status}</output>;
}

const routes: RouteObject[] = [
  {
    path: '*',
    element: (
      <div className="app">
        <CustomerTabBar />
        <AuthProbe />
      </div>
    ),
  },
];

function renderBar(path: string, fakes: AuthFakes = anonymousFakes()) {
  return {
    ...renderRoutesWithAuth(routes, { initialEntries: [path], fakes }),
    user: userEvent.setup(),
  };
}

describe('CustomerTabBar', () => {
  it('탭 3개의 라벨과 순서: 홈, 내 예약, 마이', () => {
    renderBar('/');
    expect(screen.getAllByRole('link').map((l) => l.textContent)).toEqual([
      '홈',
      '내 예약',
      '마이',
    ]);
  });

  it('/에서 홈이 aria-current="page"이고 <b>로 굵게, 나머지는 <span>', () => {
    renderBar('/');
    const home = screen.getByRole('link', { name: '홈' });
    expect(home).toHaveAttribute('aria-current', 'page');
    expect(home.parentElement?.tagName).toBe('B');
    expect(screen.getByRole('link', { name: '내 예약' })).not.toHaveAttribute('aria-current');
    expect(screen.getByRole('link', { name: '내 예약' }).parentElement?.tagName).toBe('SPAN');
  });

  it('anonymous가 「내 예약」을 누르면 /login으로 가고 state.from이 /reservations', async () => {
    const { user, router } = renderBar('/');
    await waitFor(() => expect(screen.getByTestId('auth')).toHaveTextContent('anonymous'));
    await user.click(screen.getByRole('link', { name: '내 예약' }));
    expect(router.state.location.pathname).toBe('/login');
    expect(router.state.location.state).toEqual({ from: '/reservations' });
  });

  it('anonymous가 「마이」를 누르면 state.from이 /my', async () => {
    const { user, router } = renderBar('/');
    await waitFor(() => expect(screen.getByTestId('auth')).toHaveTextContent('anonymous'));
    await user.click(screen.getByRole('link', { name: '마이' }));
    expect(router.state.location.pathname).toBe('/login');
    expect(router.state.location.state).toEqual({ from: '/my' });
  });

  it('authenticated가 「내 예약」을 누르면 /reservations로 이동한다', async () => {
    const { user, router } = renderBar('/', signedInFakes(customerUser));
    await waitFor(() => expect(screen.getByTestId('auth')).toHaveTextContent('authenticated'));
    await user.click(screen.getByRole('link', { name: '내 예약' }));
    expect(router.state.location.pathname).toBe('/reservations');
  });

  it('세션 확인 중(loading)에 누르면 경로로 이동한다(로그인으로 보내지 않는다)', async () => {
    const fakes = signedInFakes(customerUser);
    fakes.auth.findMe.mockReturnValue(deferred<User>().promise);
    const { user, router } = renderBar('/', fakes);
    expect(screen.getByTestId('auth')).toHaveTextContent('loading');
    await user.click(screen.getByRole('link', { name: '내 예약' }));
    expect(router.state.location.pathname).toBe('/reservations');
  });

  it('/offers/x 같은 하위 경로에서는 현재 탭이 없다', () => {
    renderBar('/offers/x');
    for (const link of screen.getAllByRole('link')) {
      expect(link).not.toHaveAttribute('aria-current');
    }
  });
});
