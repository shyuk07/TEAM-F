import { loginRedirectState, type AuthState } from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

export type CustomerTabKey = 'home' | 'reservations' | 'my';

export type CustomerTab = {
  key: CustomerTabKey;
  label: string;
  path: string;
  requiresLogin: boolean;
};

export type TabTarget = { to: string; state?: ReturnType<typeof loginRedirectState> };

// FIXME: 내 예약·마이 탭의 경로(/reservations, /my)에 화면이 없다. 로그인한 사용자가 누르면 홈으로 돌아온다.
//   왜: C5·C6이 아직 없다 (docs/design/frontend/offers.md D-6)
//   언제: C5 구현 시, C6 구현 시, 늦어도 배포 전
export const CUSTOMER_TABS: readonly CustomerTab[] = [
  { key: 'home', label: '홈', path: ROUTES.home, requiresLogin: false },
  { key: 'reservations', label: '내 예약', path: ROUTES.reservations, requiresLogin: true },
  { key: 'my', label: '마이', path: ROUTES.my, requiresLogin: true },
];

export function activeCustomerTab(pathname: string): CustomerTabKey | null {
  // react-router처럼 대소문자를 구분하지 않고 판정한다
  const trimmed = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
  const path = trimmed.toLowerCase();
  if (path === ROUTES.home) return 'home';
  const hit = CUSTOMER_TABS.find(
    (t) => t.key !== 'home' && (path === t.path || path.startsWith(`${t.path}/`)),
  );
  return hit ? hit.key : null;
}

export function tabTarget(tab: CustomerTab, authStatus: AuthState['status']): TabTarget {
  if (tab.requiresLogin && authStatus === 'anonymous') {
    return { to: ROUTES.login, state: loginRedirectState('other', tab.path) };
  }
  return { to: tab.path };
}
