import type { PointLog, PointPage } from '@/features/auth';
import { at } from '../../../support/clock';

// 기본: 11/07 18:02 적립 +115P, 잔액 1,240P
export function makePointLog(over: Partial<PointLog> = {}): PointLog {
  return {
    id: 'pl1',
    amount: 115,
    type: 'EARN',
    balanceAfter: 1240,
    createdAt: at(7, 18, 2),
    ...over,
  };
}

/** 최근 내역 3행: 적립 +115P / 사용 −500P / 지급 +1,000P */
export function recentLogs(): PointLog[] {
  return [
    makePointLog(),
    makePointLog({
      id: 'pl2',
      amount: -500,
      type: 'USE',
      balanceAfter: 1125,
      createdAt: at(6, 12, 0),
    }),
    makePointLog({
      id: 'pl3',
      amount: 1000,
      type: 'GRANT',
      balanceAfter: 1625,
      createdAt: at(5, 9, 0),
    }),
  ];
}

/** id가 plS…pl(S+N-1)인 적립 N개. */
export function makePointLogs(count: number, start = 1): PointLog[] {
  return Array.from({ length: count }, (_, i) => makePointLog({ id: `pl${start + i}` }));
}

export function makePointPage(
  logs: PointLog[],
  over: Partial<Omit<PointPage, 'logs'>> = {},
): PointPage {
  return { balance: 1240, logs, page: 0, size: 20, total: logs.length, ...over };
}
