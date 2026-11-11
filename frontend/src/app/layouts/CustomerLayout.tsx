import { useState } from 'react';
import { Navigate, Outlet, useLocation, useMatches } from 'react-router';
import { isTabBarHandle } from '@/app/router/handle';
import {
  SESSION_ERROR_FALLBACK_MESSAGE,
  decideAccess,
  loginRedirectState,
  useAuth,
} from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';
import { CustomerTabBar } from '@/widgets/customer-nav';
import { CustomerFrame } from './CustomerFrame';

// 고객 셸(customer-home.md §3.4, D-2·D-4). public은 가드 없이, customer는 CUSTOMER만 통과시킨다.
export function CustomerLayout({ access }: { access: 'public' | 'customer' }) {
  return access === 'public' ? <CustomerShell /> : <CustomerGuard />;
}

function CustomerShell() {
  const showTabBar = useMatches().some((m) => isTabBarHandle(m.handle));
  return (
    <CustomerFrame>
      <div className="app">
        <Outlet />
        {showTabBar ? <CustomerTabBar /> : null}
      </div>
    </CustomerFrame>
  );
}

function CustomerGuard() {
  const { state, reload } = useAuth();
  const location = useLocation();
  const decision = decideAccess(state, 'CUSTOMER');
  // 이 레이아웃이 한 번이라도 allow를 그렸는지. 방금 로그아웃·탈퇴(C10·C7)면 홈, 아니면 A1로 보낸다(D-4).
  const [wasAllowed, setWasAllowed] = useState(false);
  if (decision === 'allow' && !wasAllowed) setWasAllowed(true);

  const toLogin = (
    <Navigate
      to={ROUTES.login}
      replace
      state={loginRedirectState(
        'other',
        location.pathname + location.search + location.hash,
        'customerTab',
      )}
    />
  );

  switch (decision) {
    case 'loading':
      return (
        <CustomerFrame>
          <div className="app" aria-busy="true" />
        </CustomerFrame>
      );
    case 'login':
      return toLogin;
    case 'login-without-from':
      return wasAllowed ? <Navigate to={ROUTES.home} replace /> : toLogin;
    case 'home':
      return <Navigate to={ROUTES.home} replace />;
    case 'error':
      return (
        <CustomerFrame>
          <div className="app">
            <div className="body">
              <div className="err" role="alert">
                {state.status === 'error' && state.message !== ''
                  ? state.message
                  : SESSION_ERROR_FALLBACK_MESSAGE}
              </div>
              <button type="button" className="btn" onClick={reload}>
                다시 시도
              </button>
            </div>
          </div>
        </CustomerFrame>
      );
    case 'allow':
      return <CustomerShell />;
  }
}
