import { Navigate, Outlet, useLocation } from 'react-router';
import {
  SESSION_ERROR_FALLBACK_MESSAGE,
  decideAccess,
  loginRedirectState,
  useAuth,
} from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

// TODO: 고객 셸 정식 설계 전 임시 레이아웃이다. 로그인 가드만 두고 고객 TabBar 등 내비게이션은 없다.
//   왜: 고객 셸(TabBar widget, 고객 가드, 고객 라우트)이 설계되지 않았다 (docs/design/frontend/reservations.md C-5, D-10)
//   언제: 결정 후 (사용자: 고객 셸 설계)
// TODO: PC에서 고객 앱 컨테이너를 최대 420px·가운데·좌우 1px line·바깥 bg로 인라인 style 제한한다. 정식 고객 셸 클래스로 옮긴다.
//   왜: PC 420px 고정은 layout.md 기준(고객 PC = 모바일 화면 그대로 가운데 420px)이고, 컨테이너가 720px 미만이어야 .cta가 PC에서도 보인다. bundle.css에 고객 셸 클래스가 없다 (docs/design/frontend/reservations.md C-5)
//   언제: 결정 후 (사용자: 고객 셸 설계)
const OUTER_STYLE = { minHeight: '100%', background: 'var(--bg)' } as const;
const APP_STYLE = {
  maxWidth: 420,
  boxSizing: 'border-box',
  margin: '0 auto',
  borderLeft: '1px solid var(--line)',
  borderRight: '1px solid var(--line)',
} as const;

export function CustomerLayout() {
  const { state, reload } = useAuth();
  const location = useLocation();

  switch (decideAccess(state, 'CUSTOMER')) {
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
        <div style={OUTER_STYLE}>
          <div className="app" style={APP_STYLE}>
            <Outlet />
          </div>
        </div>
      );
  }
}
