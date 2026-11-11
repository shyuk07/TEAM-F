import { ROUTES } from '@/shared/lib/routes';

export type CustomerTabKey = 'home' | 'reservations' | 'me';

export type CustomerTab = { key: CustomerTabKey; label: string; path: string };

export const CUSTOMER_TABS: readonly CustomerTab[] = [
  { key: 'home', label: '홈', path: ROUTES.home },
  { key: 'reservations', label: '내 예약', path: ROUTES.reservations },
  { key: 'me', label: '마이', path: ROUTES.me },
];

export function activeCustomerTab(pathname: string): CustomerTabKey | null {
  // react-router처럼 대소문자를 구분하지 않고 판정한다(activeOwnerTab과 같은 방식)
  const trimmed = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
  const path = trimmed.toLowerCase();
  if (path === ROUTES.home) return 'home';
  const hit = CUSTOMER_TABS.find(
    (t) => t.path !== ROUTES.home && (path === t.path || path.startsWith(`${t.path}/`)),
  );
  return hit ? hit.key : null;
}
