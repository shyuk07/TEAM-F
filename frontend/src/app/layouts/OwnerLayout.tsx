import { Navigate, Outlet, useLocation, useMatches } from 'react-router';
import { isTabBarHandle } from '@/app/router/handle';
import {
  SESSION_ERROR_FALLBACK_MESSAGE,
  decideAccess,
  loginRedirectState,
  useAuth,
} from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';
import { OwnerTabBar } from '@/widgets/owner-nav';

// FIXME: 승인 대기·거부·정지 상점주도 가드를 통과한다. O0(승인 대기) 화면이 없다.
//   왜: stores 영역이 없어 상점 개설·승인 상태 화면을 만들 수 없다 (docs/design/frontend/auth.md D-7, C-3)
//   언제: stores 구현 시, 늦어도 배포 전
// TODO: 임시 문구다(로그인 실패 기본 문구, 세션 확인 실패 기본 문구, 「다시 시도」, 「닫기」, 「계정 메뉴」). 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/auth.md D-9)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export function OwnerLayout() {
  const showTabBar = useMatches().some((m) => isTabBarHandle(m.handle));
  const { state, reload } = useAuth();
  const location = useLocation();
  const decision = decideAccess(state, 'OWNER');

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
          <Outlet />
          {showTabBar ? <OwnerTabBar /> : null}
        </div>
      );
  }
}
