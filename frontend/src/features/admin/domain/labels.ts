import type { AdminAccountStatus, AdminUserSummary } from './adminUser';

export type Tone = 'hot' | 'ok' | 'mute' | null;
export type StatusView = { text: string; tone: Tone };

// states.md 「상점·회원」 표
const ACCOUNT_STATUS: Record<AdminAccountStatus, StatusView> = {
  PENDING: { text: '승인 대기', tone: 'hot' },
  APPROVED: { text: '정상', tone: null },
  REJECTED: { text: '거절됨', tone: 'mute' },
  SUSPENDED: { text: '정지', tone: 'hot' },
  WITHDRAWN: { text: '탈퇴', tone: 'mute' },
};

export function accountStatusView(status: AdminAccountStatus): StatusView {
  return ACCOUNT_STATUS[status];
}

const STORE_STATUS: Record<string, StatusView> = {
  ACTIVE: { text: '영업 중', tone: 'ok' },
  SUSPENDED: { text: '상점 정지', tone: 'hot' },
  CLOSED: { text: '폐점', tone: 'mute' },
};

export function storeStatusView(status: string): StatusView {
  return STORE_STATUS[status] ?? { text: status, tone: null };
}

// states.md 「할인 (상점주 화면)」 표의 관리자 정지. 다른 상태는 코드만 보인다(관리자 화면 코드 병기)
const OFFER_STATUS: Record<string, StatusView> = {
  SUSPENDED: { text: '할인 정지', tone: 'hot' },
  ON_SALE: { text: '판매 중', tone: 'ok' },
};

export function offerStatusView(status: string): StatusView {
  return OFFER_STATUS[status] ?? { text: status, tone: null };
}

// states.md 「포인트 내역 종류」 표
const POINT_TYPES: Record<string, string> = {
  EARN: '적립',
  USE: '사용',
  RESTORE: '복구',
  REVOKE: '회수',
  GRANT: '지급',
  EXPIRE: '소멸',
};

export function pointTypeLabel(type: string): string {
  return POINT_TYPES[type] ?? type;
}

export function formatPoint(n: number): string {
  return `${n.toLocaleString('ko-KR')}P`;
}

export function formatSignedPoint(n: number): string {
  // 와이어프레임의 마이너스는 U+2212
  if (n < 0) return `−${formatPoint(-n)}`;
  return `+${formatPoint(n)}`;
}

function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

export function formatShortDate(d: Date): string {
  return `${pad2(d.getMonth() + 1)}/${pad2(d.getDate())}`;
}

export function displayName(u: Pick<AdminUserSummary, 'name' | 'email'>): string {
  return u.name !== null && u.name.trim() !== '' ? u.name : u.email;
}

// 010-1234-5678 → 010-****-5678. 형식이 다르면 끝 4자리만 남긴다.
export function maskPhone(phone: string | null): string {
  if (phone === null || phone === '') return '';
  const m = /^(\d{2,3})-(\d{3,4})-(\d{4})$/.exec(phone);
  if (m) return `${m[1]}-****-${m[3]}`;
  if (phone.length <= 4) return phone;
  return `${'*'.repeat(phone.length - 4)}${phone.slice(-4)}`;
}
