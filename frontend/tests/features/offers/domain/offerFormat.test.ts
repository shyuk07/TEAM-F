import {
  formatDiscountRate,
  formatDistance,
  formatPlainPrice,
  formatRemaining,
  formatStoreLine,
  formatWon,
} from '@/features/offers/domain/offerFormat';

describe('formatWon', () => {
  it.each([
    [0, '0원'],
    [999, '999원'],
    [1000, '1,000원'],
    [11500, '11,500원'],
    [1234567, '1,234,567원'],
  ])('%i → %s', (n, expected) => {
    expect(formatWon(n)).toBe(expected);
  });
});

describe('formatPlainPrice', () => {
  it.each([
    [12000, '12,000'],
    [0, '0'],
    [999, '999'],
  ])('%i → %s', (n, expected) => {
    expect(formatPlainPrice(n)).toBe(expected);
  });
});

describe('formatDiscountRate', () => {
  it.each([
    [50, '50%'],
    [0, '0%'],
  ])('%i → %s', (rate, expected) => {
    expect(formatDiscountRate(rate)).toBe(expected);
  });
});

describe('formatDistance', () => {
  it('null이면 null', () => {
    expect(formatDistance(null)).toBeNull();
  });

  it.each([
    [0.4, '0.4km'],
    [0.35, '0.4km'],
    [0.04, '0.0km'],
    [0, '0.0km'],
    [1, '1.0km'],
    [12.34, '12.3km'],
  ])('%f → %s', (km, expected) => {
    expect(formatDistance(km)).toBe(expected);
  });
});

describe('formatStoreLine', () => {
  it('거리가 있으면 가운뎃점으로 잇는다', () => {
    expect(formatStoreLine('망원베이커리', 0.4)).toBe('망원베이커리 · 0.4km');
  });

  it('거리가 없으면 상점명만', () => {
    expect(formatStoreLine('망원베이커리', null)).toBe('망원베이커리');
  });
});

describe('formatRemaining', () => {
  it.each([
    [3, '남은 3개'],
    [0, '남은 0개'],
  ])('%i → %s', (n, expected) => {
    expect(formatRemaining(n)).toBe(expected);
  });
});
