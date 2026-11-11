import {
  amountBounds,
  signedAmount,
  stockAfter,
  validateStockAdjust,
  type Offer,
} from '@/features/offers';
import { makeOffer } from '../fakes/offers';

// 남은 3개, 최초 수량 10개 기준 offer
const baseOffer = (over: Partial<Offer> = {}): Offer => makeOffer(over);

describe('amountBounds', () => {
  it('subtract 모드: min 1, max는 남은 재고', () => {
    expect(amountBounds(baseOffer(), 'subtract')).toEqual({ min: 1, max: 3 });
  });
  it('subtract 모드: 남은 재고가 0이면 max도 0', () => {
    expect(amountBounds(baseOffer({ remainingStock: 0 }), 'subtract')).toEqual({ min: 1, max: 0 });
  });
  it('add 모드: min 1, max는 9999 - 최초 수량', () => {
    expect(amountBounds(baseOffer(), 'add')).toEqual({ min: 1, max: 9999 - 10 });
  });
  it('add 모드: 최초 수량이 9999면 max는 0', () => {
    expect(amountBounds(baseOffer({ initialStock: 9999 }), 'add')).toEqual({ min: 1, max: 0 });
  });
});

describe('signedAmount', () => {
  it('subtract 모드는 음수', () => {
    expect(signedAmount('subtract', 3)).toBe(-3);
  });
  it('add 모드는 양수', () => {
    expect(signedAmount('add', 3)).toBe(3);
  });
});

describe('stockAfter', () => {
  it('subtract 후 남은 재고 감소', () => {
    expect(stockAfter(baseOffer(), 'subtract', 2)).toBe(1);
  });
  it('add 후 남은 재고 증가', () => {
    expect(stockAfter(baseOffer(), 'add', 5)).toBe(8);
  });
});

describe('validateStockAdjust', () => {
  it('수량이 1 미만이면 amount-zero', () => {
    expect(validateStockAdjust(baseOffer(), 'subtract', 0)).toBe('amount-zero');
  });
  it('subtract에서 남은 재고 초과면 over-remaining', () => {
    expect(validateStockAdjust(baseOffer(), 'subtract', 4)).toBe('over-remaining');
  });
  it('add에서 최초 수량 + 수량이 9999 초과면 over-max', () => {
    expect(validateStockAdjust(baseOffer({ initialStock: 9995 }), 'add', 5)).toBe('over-max');
  });
  it('사유가 200자 초과면 reason-too-long', () => {
    expect(validateStockAdjust(baseOffer(), 'subtract', 1, 'a'.repeat(201))).toBe('reason-too-long');
  });
  it('유효하면 null', () => {
    expect(validateStockAdjust(baseOffer(), 'subtract', 3)).toBeNull();
    expect(validateStockAdjust(baseOffer(), 'add', 1, '사유')).toBeNull();
  });
});
