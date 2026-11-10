import { Navigate, Outlet, useLocation } from 'react-router';
import {
  SESSION_ERROR_FALLBACK_MESSAGE,
  decideAccess,
  loginRedirectState,
  useAuth,
} from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

// 역할 무관 로그인 필요 가드(C8·C9). allow면 page가 .app 프레임을 그린다(auth-account.md D-4).
// TODO: C8·C9 프레임을 고객 셸(PC 420px 가운데) 규칙과 맞춘다.
//   왜: 고객 셸이 아직 없어 역할 무관 하위 화면으로만 둔다 (auth-account.md D-4). 고객 셸은 offers.md D-5로 생겼으나 C8·C9로 가는 고객 진입점(C6)이 아직 없다 (docs/design/frontend/offers.md D-7)
//   언제: C6 구현 시
export function AccountLayout() {
  const { state, reload } = useAuth();
  const location = useLocation();
  const decision = decideAccess(state, 'ANY');

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
    case 'home':
      // 'ANY'는 'home'을 내지 않는다. 타입상 남은 경우라 OwnerLayout과 같이 홈으로 보낸다.
      return <Navigate to={ROUTES.home} replace />;
    case 'allow':
      return <Outlet />;
  }
}
