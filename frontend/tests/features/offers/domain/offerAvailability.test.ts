import {
  offerAvailability,
  unavailableMessage,
  type Offer,
  type UnavailableReason,
} from '@/features/offers';
import { makeOffer } from '../fakes/offers';

// 판정은 시각 비교만 하므로 KST 오프셋을 명시해 시간대와 관계없이 같은 순간을 쓴다.
const NOW = new Date('2026-11-04T17:30:00+09:00');
const MIN = 60_000;
const plus = (ms: number) => new Date(NOW.getTime() + ms);

function offer(over: Partial<Offer> = {}): Offer {
  return makeOffer({
    status: 'ON_SALE',
    isActive: true,
    isSoldOut: false,
    remainingStock: 3,
    salesStart: new Date('2026-11-04T16:00:00+09:00'),
    salesEnd: new Date('2026-11-04T18:00:00+09:00'),
    ...over,
  });
}

const reason = (over: Partial<Offer>) => offerAvailability(offer(over), NOW);

describe('offerAvailability', () => {
  it('ON_SALE·활성·재고 있음·판매 기간 안 → reservable', () => {
    expect(offerAvailability(offer(), NOW)).toEqual({ reservable: true });
  });

  it.each<[string, Partial<Offer>]>([
    ['remainingStock 0', { remainingStock: 0 }],
    ['isSoldOut true', { isSoldOut: true }],
    ['status SOLD_OUT', { status: 'SOLD_OUT' }],
  ])('%s → soldOut', (_name, over) => {
    expect(reason(over)).toEqual({ reservable: false, reason: 'soldOut' });
  });

  it('품절 + CLOSED → soldOut(품절 우선)', () => {
    expect(reason({ remainingStock: 0, status: 'CLOSED' })).toEqual({
      reservable: false,
      reason: 'soldOut',
    });
  });

  it.each<[Offer['status']]>([['CLOSED'], ['SUSPENDED']])('status %s → ended', (status) => {
    expect(reason({ status })).toEqual({ reservable: false, reason: 'ended' });
  });

  it('salesEnd == now(마감 정각) → ended', () => {
    expect(reason({ salesEnd: NOW })).toEqual({ reservable: false, reason: 'ended' });
  });

  it('salesEnd = now + 1ms → reservable', () => {
    expect(reason({ salesEnd: plus(1) })).toEqual({ reservable: true });
  });

  it('isActive false → inactive', () => {
    expect(reason({ isActive: false })).toEqual({ reservable: false, reason: 'inactive' });
  });

  it('status SCHEDULED → notStarted', () => {
    expect(reason({ status: 'SCHEDULED' })).toEqual({ reservable: false, reason: 'notStarted' });
  });

  it('ON_SALE이지만 salesStart = now + 1분 → notStarted', () => {
    expect(reason({ salesStart: plus(MIN) })).toEqual({ reservable: false, reason: 'notStarted' });
  });
});

describe('unavailableMessage', () => {
  it.each<[UnavailableReason, string]>([
    ['soldOut', '품절됐어요.'],
    ['ended', '판매가 종료됐어요.'],
    ['inactive', '지금은 판매하지 않는 상품이에요.'],
    ['notStarted', '아직 판매 전이에요.'],
  ])('%s → %s', (r, text) => {
    expect(unavailableMessage(r)).toBe(text);
  });
});
