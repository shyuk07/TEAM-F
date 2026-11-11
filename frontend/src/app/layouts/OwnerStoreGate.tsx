import { Navigate, Outlet, useLocation, useMatches } from 'react-router';
import { isTabBarHandle } from '@/app/router/handle';
import { MY_STORE_ERROR_FALLBACK_MESSAGE, decideOwnerEntry, useMyStore } from '@/entities/store';
import { ROUTES } from '@/shared/lib/routes';
import { OwnerTabBar } from '@/widgets/owner-nav';

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
