import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { type RouteObject } from 'react-router';
import { OwnerLayout } from '@/app/layouts/OwnerLayout';
import { useAuth } from '@/features/auth';
import { ApiError } from '@/shared/api/error';
import { OwnerTopNav } from '@/widgets/owner-nav';
import { deferred } from '../../features/auth/fakes/deferred';
import { adminUser, customerUser, ownerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';
import type { User } from '@/features/auth';
import { renderRoutesWithOwnerStore } from '../../support/renderWithOwnerStore';

function Page() {
  return (
    <>
      <p>본문</p>
      <OwnerTopNav />
    </>
  );
}

async function renderLayout(tabBar: boolean) {
  const testRoutes: RouteObject[] = [
    {
      element: <OwnerLayout />,
      children: [
        { path: '/owner/today', element: <Page />, handle: tabBar ? { tabBar: true } : {} },
      ],
    },
  ];
  const result = renderRoutesWithAuth(testRoutes, {
    initialEntries: ['/owner/today'],
    fakes: signedInFakes(),
  });
  await screen.findByText('본문');
  return result;
}

describe('OwnerLayout', () => {
  it('handle.tabBar가 true면 TabBar가 Outlet 내용 뒤에 온다', async () => {
    await renderLayout(true);
    const tabs = document.querySelector('.tabs');
    expect(tabs).not.toBeNull();
    const nav = screen.getByText('본문').parentElement;
    expect(nav?.lastElementChild).toBe(tabs);
  });

  it('handle.tabBar가 없으면 TabBar가 없다', async () => {
    await renderLayout(false);
    expect(document.querySelector('.tabs')).toBeNull();
    expect(screen.getAllByRole('link', { name: '오늘' })).toHaveLength(1);
  });

  it('프레임 요소에 app 클래스가 있다', async () => {
    const { container } = await renderLayout(true);
    expect(container.firstElementChild).toHaveClass('app');
  });

  it('탭 화면에서 「오늘」 링크가 TabBar와 TopNav 두 곳에 있다', async () => {
    await renderLayout(true);
    expect(screen.getAllByRole('link', { name: '오늘' })).toHaveLength(2);
  });
});

function LogoutTrigger() {
  const { logout } = useAuth();
  return (
    <button type="button" onClick={() => void logout()}>
      테스트 로그아웃
    </button>
  );
}

function renderGuard(fakes: AuthFakes, path = '/owner/today') {
  const routes: RouteObject[] = [
    { path: '/login', element: <p>로그인 화면</p> },
    { path: '/', element: <p>홈 화면</p> },
    {
      element: <OwnerLayout />,
      children: [
        {
          path: '/owner/today',
          element: (
            <>
              <p>본문</p>
              <LogoutTrigger />
            </>
          ),
          handle: { tabBar: true },
        },
      ],
    },
  ];
  return renderRoutesWithAuth(routes, { initialEntries: [path], fakes });
}

describe('OwnerLayout 인증 가드', () => {
  it('세션 확인 중에는 본문도 TabBar도 없고 aria-busy 프레임만 있다', () => {
    const fakes = signedInFakes();
    const d = deferred<User>();
    fakes.auth.findMe.mockReturnValue(d.promise);
    renderGuard(fakes);
    expect(screen.queryByText('본문')).not.toBeInTheDocument();
    expect(document.querySelector('.tabs')).toBeNull();
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
  });

  it('anonymous(other)면 /login으로 이동하고 state.from이 원래 경로다', async () => {
    const { router } = renderGuard(anonymousFakes());
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/owner/today' });
  });

  it('쿼리가 있는 경로면 from에 쿼리가 포함된다', async () => {
    const { router } = renderGuard(anonymousFakes(), '/owner/today?x=1');
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/owner/today?x=1' });
  });

  it('직접 로그아웃하면 /login으로 이동하고 state는 null이다', async () => {
    const { router } = renderGuard(signedInFakes());
    await userEvent.click(await screen.findByRole('button', { name: '테스트 로그아웃' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toBeNull();
  });

  it('CUSTOMER면 /로 이동한다', async () => {
    const { router } = renderGuard(signedInFakes(customerUser));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });

  it('ADMIN이면 /로 이동한다', async () => {
    const { router } = renderGuard(signedInFakes(adminUser));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });

  it('승인 대기(PENDING) OWNER도 본문이 보인다', async () => {
    renderGuard(signedInFakes({ ...ownerUser, status: 'PENDING' }));
    expect(await screen.findByText('본문')).toBeInTheDocument();
  });

  it('error면 오류 문구와 「다시 시도」가 있고 누르면 재시도 성공 뒤 본문이 보인다', async () => {
    const fakes = signedInFakes();
    fakes.auth.findMe.mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', '네트워크 문구'));
    renderGuard(fakes);
    expect(await screen.findByText('네트워크 문구')).toBeInTheDocument();
    expect(screen.queryByText('본문')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByText('본문')).toBeInTheDocument();
  });

  it('인증된 뒤 다른 탭 로그아웃(emit false)이면 /login으로 가고 from을 남긴다', async () => {
    const fakes = signedInFakes();
    const { router } = renderGuard(fakes);
    await screen.findByText('본문');
    fakes.session.emit(false);
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/owner/today' });
  });
});

describe('OwnerLayout error 대체 문구', () => {
  it('message가 빈 오류면 alert에 대체 문구가 보인다', async () => {
    const fakes = signedInFakes();
    fakes.auth.findMe.mockRejectedValueOnce(new ApiError(500, 'INTERNAL_ERROR', ''));
    renderGuard(fakes);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('불러오지 못했어요. 잠시 후 다시 시도해 주세요.');
  });
});

describe('OwnerLayout 가드가 상점 조회를 시작하지 않는 경우', () => {
  const routes: RouteObject[] = [
    { path: '/login', element: <p>로그인 화면</p> },
    { path: '/', element: <p>홈 화면</p> },
    {
      element: <OwnerLayout />,
      children: [{ path: '/owner/today', element: <p>본문</p>, handle: { tabBar: true } }],
    },
  ];

  it('로그인 안 함(anonymous) → 상점 조회(findMine)를 시작하지 않는다', async () => {
    const { router, repo } = renderRoutesWithOwnerStore(routes, {
      initialEntries: ['/owner/today'],
      fakes: anonymousFakes(),
    });
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(repo.findMine).not.toHaveBeenCalled();
  });

  it('CUSTOMER → 홈으로 갈 때 상점 조회(findMine)를 시작하지 않는다', async () => {
    const { router, repo } = renderRoutesWithOwnerStore(routes, {
      initialEntries: ['/owner/today'],
      fakes: signedInFakes(customerUser),
    });
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(repo.findMine).not.toHaveBeenCalled();
  });
});
