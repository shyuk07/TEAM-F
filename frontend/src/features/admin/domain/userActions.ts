import type { AdminUserSummary } from './adminUser';

export type UserActions = { grantPoints: boolean; suspend: boolean; withdraw: boolean };

// 서버가 막는 동작은 미리 숨긴다 (admin.md D-11, reference/admin.md §3·§4·§9)
// - 탈퇴 회원: USER_WITHDRAWN / USER_ALREADY_WITHDRAWN
// - 관리자 계정: ADMIN_ACCOUNT_PROTECTED
// - 정지 중: USER_ALREADY_SUSPENDED, 승인 대기·거절 상점주: USER_NOT_SUSPENDABLE
export function availableUserActions(u: Pick<AdminUserSummary, 'role' | 'status'>): UserActions {
  if (u.status === 'WITHDRAWN') return { grantPoints: false, suspend: false, withdraw: false };
  const isAdmin = u.role === 'ADMIN';
  return {
    grantPoints: true,
    suspend: !isAdmin && u.status === 'APPROVED',
    withdraw: !isAdmin,
  };
}

/** 승인·거부 버튼은 승인 대기 상점주에게만 (reference/admin.md §1 OWNER_NOT_PENDING) */
export function canReview(u: Pick<AdminUserSummary, 'role' | 'status'>): boolean {
  return u.role === 'OWNER' && u.status === 'PENDING';
}
