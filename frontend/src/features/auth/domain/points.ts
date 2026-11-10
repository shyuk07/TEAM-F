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

export function pointTypeLabel(t: PointType): string {
  void t;
  throw new Error('not implemented: pointTypeLabel');
}

export function formatPoint(n: number): string {
  void n;
  throw new Error('not implemented: formatPoint');
}

export function formatPointDelta(n: number): string {
  void n;
  throw new Error('not implemented: formatPointDelta');
}

export function pointLogMeta(log: PointLog, variant: 'short' | 'full'): string {
  void log;
  void variant;
  throw new Error('not implemented: pointLogMeta');
}

export function pointExpiryText(balance: number): string {
  void balance;
  throw new Error('not implemented: pointExpiryText');
}
