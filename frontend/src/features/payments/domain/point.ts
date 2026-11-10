export const POINT_UNIT = 100;
const EARN_MIN_AMOUNT = 100;
const EARN_RATE_PERCENT = 1;

export type PointInputError = 'notInteger' | 'notUnit' | 'overBalance' | 'overTotal' | null;

// 100P 단위로 내림(REQ-17·21·27). 총액 끝자리(100 미만)는 포인트로 낼 수 없다.
export function maxUsablePoint(balance: number, total: number): number {
  const cap = Math.min(balance, total);
  if (cap <= 0) return 0;
  return Math.floor(cap / POINT_UNIT) * POINT_UNIT;
}

export function validatePointInput(
  raw: string,
  balance: number,
  total: number,
): { value: number; error: PointInputError } {
  const text = raw.trim();
  if (text === '') return { value: 0, error: null };
  if (!/^\d+$/.test(text)) return { value: 0, error: 'notInteger' };
  const value = Number(text);
  if (value % POINT_UNIT !== 0) return { value, error: 'notUnit' };
  if (value > balance) return { value, error: 'overBalance' };
  if (value > total) return { value, error: 'overTotal' };
  return { value, error: null };
}

export function payAmount(total: number, usePoint: number): number {
  return total - usePoint;
}

// 1% 버림(REQ-18), 99원 이하 미적립(REQ-26).
export function earnPreview(amount: number): number {
  if (amount < EARN_MIN_AMOUNT) return 0;
  return Math.floor((amount * EARN_RATE_PERCENT) / 100);
}
