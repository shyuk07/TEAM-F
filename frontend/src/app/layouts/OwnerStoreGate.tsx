import { Navigate, Outlet, useLocation, useMatches } from 'react-router';
import { isTabBarHandle } from '@/app/router/handle';
import {
  MY_STORE_ERROR_FALLBACK_MESSAGE,
  decideOwnerEntry,
  useMyStore,
} from '@/entities/store';
import { ROUTES } from '@/shared/lib/routes';
import { OwnerTabBar } from '@/widgets/owner-nav';

// FIXME: 상점이 정지되어도 O1에 정지 안내가 고정되지 않는다. 가드는 O1로 보내기만 한다.
//   왜: O1 화면이 자리 page라 StoreSuspendedNotice를 놓을 곳이 없다 (docs/design/frontend/stores.md §4.4)
//   언제: O1 구현 시, 늦어도 배포 전
export function OwnerStoreGate() {
  const { lookup, reload } = useMyStore();
  const { pathname } = useLocation();
  const showTabBar = useMatches().some((m) => isTabBarHandle(m.handle));
  const decision = decideOwnerEntry({ lookup, onStartPage: pathname === ROUTES.ownerStart });

  switch (decision) {
    case 'loading':
      return <div className="app" aria-busy="true" />;
    case 'error':
      return (
        <div className="app">
          <div className="body">
            <div className="err" role="alert">
              {lookup.status === 'error' && lookup.message !== ''
                ? lookup.message
                : MY_STORE_ERROR_FALLBACK_MESSAGE}
            </div>
            <button type="button" className="btn" onClick={reload}>
              다시 시도
            </button>
          </div>
        </div>
      );
    case 'to-start':
      return <Navigate to={ROUTES.ownerStart} replace />;
    case 'to-today':
      return <Navigate to={ROUTES.ownerToday} replace />;
    case 'allow':
      return (
        <div className="app">
          <Outlet />
          {showTabBar ? <OwnerTabBar /> : null}
        </div>
      );
  }
}
