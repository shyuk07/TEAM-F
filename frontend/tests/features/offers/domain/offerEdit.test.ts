import {
  quantityFloor,
  diffOfferChanges,
  hasChanges,
  isEditable,
  type Offer,
  type OfferEditValues,
} from '@/features/offers';
import { makeOffer } from '../fakes/offers';

const baseOffer = (over: Partial<Offer> = {}): Offer =>
  makeOffer({
    status: 'ON_SALE',
    isActive: true,
    ...over,
  });

const values = (over: Partial<OfferEditValues> = {}): OfferEditValues => {
  const offer = baseOffer();
  return {
    salePrice: offer.salePrice,
    initialStock: offer.initialStock,
    salesEnd: offer.salesEnd,
    pickupStart: offer.pickupStart,
    pickupEnd: offer.pickupEnd,
    ...over,
  };
};

describe('quantityFloor', () => {
  it('줄어든 수가 0이면 최솟값은 1', () => {
    expect(quantityFloor(baseOffer({ initialStock: 10, remainingStock: 10 }))).toBe(1);
  });
  it('줄어든 수만큼이 최솟값 (10 중 3개 판매 → 3)', () => {
    expect(quantityFloor(baseOffer({ initialStock: 10, remainingStock: 7 }))).toBe(3);
  });
});

describe('diffOfferChanges & hasChanges', () => {
  it('변경된 필드만 추출한다', () => {
    const offer = baseOffer();
    const nextSalesEnd = new Date(offer.salesEnd.getTime() + 60 * 60 * 1000);
    const changes = diffOfferChanges(offer, values({ salePrice: 5000, salesEnd: nextSalesEnd }));

    expect(changes.salePrice).toBe(5000);
    expect(changes.salesEnd).toEqual(nextSalesEnd);
    expect(changes.initialStock).toBeUndefined();
    expect(changes.pickupStart).toBeUndefined();
    expect(changes.pickupEnd).toBeUndefined();
  });

  it('변경이 없으면 빈 객체이고 hasChanges는 false', () => {
    const offer = baseOffer();
    const changes = diffOfferChanges(offer, values());
    expect(changes).toEqual({});
    expect(hasChanges(changes)).toBe(false);
  });

  it('변경이 있으면 hasChanges는 true', () => {
    const offer = baseOffer();
    const changes = diffOfferChanges(offer, values({ initialStock: 8 }));
    expect(hasChanges(changes)).toBe(true);
  });
});

describe('isEditable', () => {
  it('활성 + 판매중/예정/품절 상태면 수정 가능', () => {
    expect(isEditable(baseOffer({ status: 'ON_SALE' }))).toBe(true);
    expect(isEditable(baseOffer({ status: 'SCHEDULED' }))).toBe(true);
    expect(isEditable(baseOffer({ status: 'SOLD_OUT' }))).toBe(true);
  });
  it('비활성이거나 종료·정지 상태면 수정 불가', () => {
    expect(isEditable(baseOffer({ isActive: false }))).toBe(false);
    expect(isEditable(baseOffer({ status: 'CLOSED' }))).toBe(false);
    expect(isEditable(baseOffer({ status: 'SUSPENDED' }))).toBe(false);
  });
});
