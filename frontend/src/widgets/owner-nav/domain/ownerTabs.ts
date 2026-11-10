import { ROUTES } from '@/shared/lib/routes';

export type OwnerTabKey = 'today' | 'offers' | 'store';

export type OwnerTab = { key: OwnerTabKey; label: string; path: string };

export const OWNER_TABS: readonly OwnerTab[] = [
  { key: 'today', label: '오늘', path: ROUTES.ownerToday },
  { key: 'offers', label: '할인', path: ROUTES.ownerOffers },
  { key: 'store', label: '매장', path: ROUTES.ownerStore },
];

export function activeOwnerTab(pathname: string): OwnerTabKey | null {
  void pathname;
  throw new Error('not implemented: activeOwnerTab');
}
