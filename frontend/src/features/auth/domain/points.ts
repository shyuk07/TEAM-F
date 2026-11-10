import { formatHm, formatMd, groupDigits } from '@/shared/lib/format';

export type PointType = 'EARN' | 'USE' | 'RESTORE' | 'REVOKE' | 'GRANT' | 'EXPIRE';

export const POINT_TYPES: readonly PointType[] = [
  'EARN',
  'USE',
  'RESTORE',
  'REVOKE',
  'GRANT',
  'EXPIRE',
];

export type PointLog = {
  id: string;
  amount: number;
  type: PointType;
  balanceAfter: number | null;
  createdAt: Date;
};

export type PointPage = {
  balance: number;
  logs: PointLog[];
  page: number;
  size: number;
  total: number;
};

export const POINT_PAGE_SIZE = 20;

export const RECENT_POINT_COUNT = 3;

// states.md 포인트 내역 종류
const POINT_TYPE_LABELS: Record<PointType, string> = {
  EARN: '적립',
  USE: '사용',
  RESTORE: '복구',
  REVOKE: '회수',
  GRANT: '지급',
  EXPIRE: '소멸',
};

export function pointTypeLabel(t: PointType): string {
  return POINT_TYPE_LABELS[t];
}

export function formatPoint(n: number): string {
  return `${groupDigits(n)}P`;
}

// 음수 기호는 U+2212(−), content.md·와이어프레임 표기
export function formatPointDelta(n: number): string {
  if (n > 0) return `+${groupDigits(n)}P`;
  if (n < 0) return `−${groupDigits(-n)}P`;
  return '0P';
}

// short: C6 최근 내역(날짜만). full: C11(날짜 시각 · 잔액, 잔액 없는 옛 내역은 생략).
export function pointLogMeta(log: PointLog, variant: 'short' | 'full'): string {
  const md = formatMd(log.createdAt);
  if (variant === 'short') return md;
  const when = `${md} ${formatHm(log.createdAt)}`;
  return log.balanceAfter === null ? when : `${when} · 잔액 ${formatPoint(log.balanceAfter)}`;
}

export function pointExpiryText(balance: number): string {
  return `${formatPoint(balance)} 소멸`;
}
