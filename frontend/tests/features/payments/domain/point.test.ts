import {
  earnPreview,
  maxUsablePoint,
  payAmount,
  validatePointInput,
} from '@/features/payments/domain/point';
import { formatPoint, formatWon } from '@/features/payments/domain/format';

describe('maxUsablePoint', () => {
  it.each([
    [1240, 11500, 1200],
    [50000, 11550, 11500],
    [99, 5000, 0],
    [0, 5000, 0],
    [1000, 0, 0],
  ])('보유 %i, 총액 %i → %i', (balance, total, expected) => {
    expect(maxUsablePoint(balance, total)).toBe(expected);
  });
});

describe('validatePointInput', () => {
  it('빈 문자열은 0, 오류 없음', () => {
    expect(validatePointInput('', 1240, 11500)).toEqual({ value: 0, error: null });
  });

  it('500은 오류 없음', () => {
    expect(validatePointInput('500', 1240, 11500)).toEqual({ value: 500, error: null });
  });

  it('550은 notUnit', () => {
    expect(validatePointInput('550', 1240, 11500).error).toBe('notUnit');
  });

  it('보유보다 많은 1300은 overBalance', () => {
    expect(validatePointInput('1300', 1240, 11500).error).toBe('overBalance');
  });

  it('보유 50000·총액 11550에서 11600은 overTotal', () => {
    expect(validatePointInput('11600', 50000, 11550).error).toBe('overTotal');
  });

  it.each(['abc', '-100', '1.5'])('%s는 notInteger', (raw) => {
    expect(validatePointInput(raw, 1240, 11500).error).toBe('notInteger');
  });
});

describe('payAmount', () => {
  it.each([
    [11500, 500, 11000],
    [11500, 0, 11500],
    [11500, 11500, 0],
  ])('총액 %i, 포인트 %i → %i', (total, use, expected) => {
    expect(payAmount(total, use)).toBe(expected);
  });
});

describe('earnPreview (1% 버림, 99원 이하 0)', () => {
  it.each([
    [11500, 115],
    [99, 0],
    [100, 1],
    [0, 0],
    [199, 1],
  ])('결제 금액 %i → %iP', (amount, expected) => {
    expect(earnPreview(amount)).toBe(expected);
  });
});

describe('format', () => {
  it('formatPoint(1240) → 1,240P', () => {
    expect(formatPoint(1240)).toBe('1,240P');
  });

  it('formatWon(11500) → 11,500원', () => {
    expect(formatWon(11500)).toBe('11,500원');
  });
});
