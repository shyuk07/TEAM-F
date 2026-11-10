import { ROUTES } from '@/shared/lib/routes';

export type OwnerTabKey = 'today' | 'offers' | 'store';

export type OwnerTab = { key: OwnerTabKey; label: string; path: string };

export const OWNER_TABS: readonly OwnerTab[] = [
  { key: 'today', label: '오늘', path: ROUTES.ownerToday },
  { key: 'offers', label: '할인', path: ROUTES.ownerOffers },
  { key: 'store', label: '매장', path: ROUTES.ownerStore },
];

// 하위 화면은 소속 탭으로 본다: 할인 등록 → 할인, 상품 등록·수정 → 매장 (app-shell.md Q-3)
const TAB_PREFIXES: readonly { key: OwnerTabKey; prefix: string }[] = [
  { key: 'today', prefix: ROUTES.ownerToday },
  { key: 'offers', prefix: ROUTES.ownerOffers },
  { key: 'store', prefix: ROUTES.ownerStore },
  { key: 'store', prefix: ROUTES.ownerProducts },
];

export function activeOwnerTab(pathname: string): OwnerTabKey | null {
  // react-router처럼 대소문자를 구분하지 않고 판정한다
  const trimmed = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
  const path = trimmed.toLowerCase();
  const hit = TAB_PREFIXES.find((t) => path === t.prefix || path.startsWith(`${t.prefix}/`));
  return hit ? hit.key : null;
}
