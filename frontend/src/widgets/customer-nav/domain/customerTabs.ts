import { ROUTES } from '@/shared/lib/routes';

export type CustomerTabKey = 'home' | 'reservations' | 'me';

export type CustomerTab = { key: CustomerTabKey; label: string; path: string };

export const CUSTOMER_TABS: readonly CustomerTab[] = [
  { key: 'home', label: '홈', path: ROUTES.home },
  { key: 'reservations', label: '내 예약', path: ROUTES.reservations },
  { key: 'me', label: '마이', path: ROUTES.me },
];

export function activeCustomerTab(pathname: string): CustomerTabKey | null {
  void pathname;
  throw new Error('not implemented: activeCustomerTab');
}
