import { useContext } from 'react';
import { Navigate, Outlet, useLocation, useMatches } from 'react-router';
import { isTabBarHandle } from '@/app/router/handle';
import { MyStoreProvider, StoreRepositoryToken } from '@/entities/store';
import {
  SESSION_ERROR_FALLBACK_MESSAGE,
  decideAccess,
  loginRedirectState,
  useAuth,
} from '@/features/auth';
import { DepsContext } from '@/shared/lib/di';
import { ROUTES } from '@/shared/lib/routes';
import { OwnerTabBar } from '@/widgets/owner-nav';
import { OwnerStoreGate } from './OwnerStoreGate';

// 상점 가드는 StoreRepositoryToken이 등록된 컨테이너에서만 마운트한다. 실앱 컨테이너는
// 항상 등록하므로 동작은 불변이고, store 가짜가 없는 가벼운 인증 단위 테스트 컨테이너에서는
// 기존 프레임으로 폴백해 가드가 findMine을 시작하지 않는다(발주자 승인 Q-2).
function useStoreGuardAvailable(): boolean {
  const container = useContext(DepsContext);
  if (!container) return false;
  try {
    container.get(StoreRepositoryToken);
    return true;
  } catch {
    return false;
  }
}

// TODO: 임시 문구다(로그인 실패 기본 문구, 세션 확인 실패 기본 문구, 「다시 시도」, 「닫기」, 「계정 메뉴」). 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/auth.md D-9)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export function OwnerLayout() {
  const showTabBar = useMatches().some((m) => isTabBarHandle(m.handle));
  const storeGuardAvailable = useStoreGuardAvailable();
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
      if (state.status !== 'authenticated' || !storeGuardAvailable) {
        return (
          <div className="app">
            <Outlet />
            {showTabBar ? <OwnerTabBar /> : null}
          </div>
        );
      }
      return (
        <MyStoreProvider key={state.user.id}>
          <OwnerStoreGate />
        </MyStoreProvider>
      );
  }
}
