import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RouteObject } from 'react-router';
import { CustomerLayout } from '@/app/layouts/CustomerLayout';
import { TAB_BAR_HANDLE } from '@/app/router/handle';
import { useAuth, type User } from '@/features/auth';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser, ownerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';

function LogoutTrigger() {
  const { logout, state } = useAuth();
  return (
    <>
      <span>{`상태:${state.status}`}</span>
      <button type="button" onClick={() => void logout()}>
        테스트 로그아웃
      </button>
    </>
  );
}

const testRoutes: RouteObject[] = [
  { path: '/login', element: <p>로그인 화면</p> },
  {
    element: <CustomerLayout access="public" />,
    children: [
      {
        path: '/',
        element: (
          <>
            <p>홈 본문</p>
            <LogoutTrigger />
          </>
        ),
        handle: TAB_BAR_HANDLE,
      },
    ],
  },
  {
    element: <CustomerLayout access="customer" />,
    children: [
      {
        path: '/me',
        element: (
          <>
            <p>마이 본문</p>
            <LogoutTrigger />
          </>
        ),
        handle: TAB_BAR_HANDLE,
      },
      { path: '/me/points', element: <p>포인트 본문</p> },
      { path: '/reservations', element: <p>예약 본문</p>, handle: TAB_BAR_HANDLE },
    ],
  },
];

function renderAt(path: string, fakes: AuthFakes) {
  return renderRoutesWithAuth(testRoutes, { initialEntries: [path], fakes });
}

const customerNav = () => screen.queryByRole('navigation', { name: '고객 메뉴' });

describe('CustomerLayout', () => {
  it('public + 비로그인: 본문과 탭 바가 고객 프레임 안에 보인다', async () => {
    renderAt('/', anonymousFakes());
    expect(await screen.findByText('홈 본문')).toBeInTheDocument();
    expect(customerNav()).toBeInTheDocument();
    const frame = document.querySelector('[data-shell="customer"]');
    expect(frame).not.toBeNull();
    expect(frame?.querySelector('.app')).toContainElement(screen.getByText('홈 본문'));
    // 높이·스크롤은 bundle.css의 .app이 맡는다. 프레임과 .app에 높이 관련 인라인을 두지 않는다.
    const app = frame?.querySelector<HTMLElement>('.app');
    expect(app?.style.flex).toBe('');
    expect(app?.style.height).toBe('');
    expect((frame as HTMLElement).style.minHeight).toBe('');
  });

  it("customer + 비로그인: /login으로 가고 state는 {from:'/me?x=1', entry:'customerTab'}", async () => {
    const { router } = renderAt('/me?x=1', anonymousFakes());
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/me?x=1', entry: 'customerTab' });
  });

  it('customer + OWNER: /로 보낸다', async () => {
    const { router } = renderAt('/me', signedInFakes(ownerUser));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(await screen.findByText('홈 본문')).toBeInTheDocument();
  });

  it('customer + 세션 확인 중: aria-busy 프레임만 있고 본문은 없다', async () => {
    const fakes = signedInFakes(customerUser);
    fakes.auth.findMe.mockReturnValue(deferred<User>().promise);
    renderAt('/me', fakes);
    await waitFor(() => expect(document.querySelector('[aria-busy="true"]')).not.toBeNull());
    expect(document.querySelector('[data-shell="customer"]')).not.toBeNull();
    expect(screen.queryByText('마이 본문')).not.toBeInTheDocument();
  });

  it('이 화면을 보다가 로그아웃(loggedOut)하면 /로 간다', async () => {
    const { router } = renderAt('/me', signedInFakes(customerUser));
    await userEvent.click(await screen.findByRole('button', { name: '테스트 로그아웃' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });

  it('로그아웃한 뒤 나중에 /reservations로 가면 /login(from 있음, entry customerTab)', async () => {
    const { router } = renderAt('/', signedInFakes(customerUser));
    await userEvent.click(await screen.findByRole('button', { name: '테스트 로그아웃' }));
    expect(await screen.findByText('상태:anonymous')).toBeInTheDocument();
    await act(async () => {
      await router.navigate('/reservations');
    });
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/reservations', entry: 'customerTab' });
  });

  it('탭 바: 현재 탭 링크는 <b> 안에 aria-current="page", handle 없는 라우트는 탭이 없다', async () => {
    const { router } = renderAt('/me', signedInFakes(customerUser));
    expect(await screen.findByText('마이 본문')).toBeInTheDocument();
    const nav = customerNav();
    expect(nav).not.toBeNull();
    const me = within(nav as HTMLElement).getByRole('link', { name: '마이' });
    expect(me).toHaveAttribute('aria-current', 'page');
    expect(me).toHaveAttribute('href', '/me');
    expect(me.parentElement?.tagName).toBe('B');
    const home = within(nav as HTMLElement).getByRole('link', { name: '홈' });
    expect(home).not.toHaveAttribute('aria-current');
    expect(within(nav as HTMLElement).getByRole('link', { name: '내 예약' })).toHaveAttribute(
      'href',
      '/reservations',
    );
    await act(async () => {
      await router.navigate('/me/points');
    });
    expect(await screen.findByText('포인트 본문')).toBeInTheDocument();
    expect(customerNav()).not.toBeInTheDocument();
  });
});
