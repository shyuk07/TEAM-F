import { ROUTES } from '@/shared/lib/routes';

export type AdminTabKey = 'approvals' | 'users' | 'stores' | 'offers';

export type AdminTab = { key: AdminTabKey; label: string; path: string };

export const ADMIN_TABS: readonly AdminTab[] = [
  { key: 'approvals', label: '승인', path: ROUTES.adminApprovals },
  { key: 'users', label: '회원', path: ROUTES.adminUsers },
  { key: 'stores', label: '상점', path: ROUTES.adminStores },
  { key: 'offers', label: '할인', path: ROUTES.adminOffers },
];

// 하위 화면은 소속 탭으로 본다: 회원 상세(/admin/users/:id) → 회원
export function activeAdminTab(pathname: string): AdminTabKey | null {
  // react-router처럼 대소문자를 구분하지 않고 판정한다
  const trimmed = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
  const path = trimmed.toLowerCase();
  const hit = ADMIN_TABS.find((t) => path === t.path || path.startsWith(`${t.path}/`));
  return hit ? hit.key : null;
}
