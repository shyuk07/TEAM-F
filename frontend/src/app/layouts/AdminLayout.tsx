import { Navigate, Outlet, useLocation, useMatches } from 'react-router';
import { isTabBarHandle } from '@/app/router/handle';
import {
  SESSION_ERROR_FALLBACK_MESSAGE,
  decideAccess,
  loginRedirectState,
  useAuth,
} from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';
import { AdminTabBar, AdminTopNav } from '@/widgets/admin-nav';
import { OwnerAccountButton } from '@/widgets/owner-nav';

// 관리자 셸: 관리자 계정만 통과시킨다. 모든 관리자 화면의 상단 바가 같아 레이아웃이 그린다 (docs/design/frontend/admin.md §1, D-1, D-12)
export function AdminLayout() {
  const showTabBar = useMatches().some((m) => isTabBarHandle(m.handle));
  const { state, reload } = useAuth();
  const location = useLocation();
  const decision = decideAccess(state, 'ADMIN');

  switch (decision) {
    case 'loading':
      return <div className="app" aria-busy="true" />;
    case 'login':
      return (
        <Navigate
          to={ROUTES.login}
          replace
          state={loginRedirectState('other', location.pathname + location.search + location.hash)}
        />
      );
    case 'login-without-from':
      return <Navigate to={ROUTES.login} replace />;
    case 'home':
      return <Navigate to={ROUTES.home} replace />;
    case 'error':
      return (
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
      );
    case 'allow':
      return (
        <div className="app">
          <div className="bar">
            <span className="logo">관리자</span>
            <span className="sp"></span>
            <AdminTopNav />
            <OwnerAccountButton />
          </div>
          <Outlet />
          {showTabBar ? <AdminTabBar /> : null}
        </div>
      );
  }
}
