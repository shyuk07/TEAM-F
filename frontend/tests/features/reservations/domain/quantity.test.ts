import {
  canDecrease,
  canIncrease,
  canReserve,
  clampQuantity,
  maxQuantity,
} from '@/features/reservations/domain/quantity';

describe('maxQuantity', () => {
  it.each([
    [10, 5],
    [5, 5],
    [3, 3],
    [1, 1],
    [0, 0],
    [-1, 0],
  ])('재고 %i → %i', (stock, expected) => {
    expect(maxQuantity(stock)).toBe(expected);
  });
});

describe('canIncrease', () => {
  it.each([
    [4, 10, true],
    [5, 10, false],
    [3, 3, false],
  ])('수량 %i, 재고 %i → %s', (q, stock, expected) => {
    expect(canIncrease(q, stock)).toBe(expected);
  });
});

describe('canDecrease', () => {
  it.each([
    [2, true],
    [1, false],
  ])('수량 %i → %s', (q, expected) => {
    expect(canDecrease(q)).toBe(expected);
  });
});

describe('canReserve', () => {
  it.each([
    [0, 10, false],
    [1, 10, true],
    [5, 10, true],
    [6, 10, false],
    [1, 0, false],
  ])('수량 %i, 재고 %i → %s', (q, stock, expected) => {
    expect(canReserve(q, stock)).toBe(expected);
  });
});

describe('clampQuantity', () => {
  it('상한보다 크면 상한으로 줄인다', () => {
    expect(clampQuantity(7, 3)).toBe(3);
  });

  it('1보다 작으면 1로 올린다', () => {
    expect(clampQuantity(0, 3)).toBe(1);
  });
});
