import {
  formatPickupWindow,
  formatSalesEndLabel,
  minutesUntilSalesEnd,
  offerCardState,
} from '@/features/offers/domain/offerCard';
import { makeOffer, minutesFromNow, now } from '../fakes/offers';

const salesEndIn = (ms: number) => makeOffer({ salesEnd: new Date(now.getTime() + ms) });

describe('minutesUntilSalesEnd', () => {
  it.each([
    ['+42분', 42 * 60_000, 42],
    ['+41분 30초(올림)', 41 * 60_000 + 30_000, 42],
    ['+1초(올림)', 1000, 1],
    ['정각', 0, 0],
    ['과거(0 미만은 0)', -5 * 60_000, 0],
    ['+60분', 60 * 60_000, 60],
  ])('%s → %i', (_name, ms, expected) => {
    expect(minutesUntilSalesEnd(salesEndIn(ms), now)).toBe(expected);
  });
});

describe('formatSalesEndLabel', () => {
  it.each([
    [1, '판매 마감 1분 전'],
    [42, '판매 마감 42분 전'],
    [59, '판매 마감 59분 전'],
    [60, '판매 마감 1시간 전'],
    [70, '판매 마감 1시간 10분 전'],
    [125, '판매 마감 2시간 5분 전'],
    [1500, '판매 마감 25시간 전'],
  ])('%i분 → %s', (minutes, expected) => {
    expect(formatSalesEndLabel(minutes)).toBe(expected);
  });
});

describe('offerCardState', () => {
  it('ON_SALE·남은 3·마감 미래 → onSale', () => {
    expect(offerCardState(makeOffer(), now)).toBe('onSale');
  });

  it('SOLD_OUT → soldOut', () => {
    expect(offerCardState(makeOffer({ status: 'SOLD_OUT', remainingStock: 0 }), now)).toBe(
      'soldOut',
    );
  });

  it('ON_SALE이지만 remainingStock 0 → soldOut', () => {
    expect(offerCardState(makeOffer({ status: 'ON_SALE', remainingStock: 0 }), now)).toBe(
      'soldOut',
    );
  });

  it('salesEnd가 정확히 now → ended(정각은 마감)', () => {
    expect(offerCardState(salesEndIn(0), now)).toBe('ended');
  });

  it('salesEnd가 now+1초 → onSale', () => {
    expect(offerCardState(salesEndIn(1000), now)).toBe('onSale');
  });

  it('CLOSED → ended', () => {
    expect(offerCardState(makeOffer({ status: 'CLOSED' }), now)).toBe('ended');
  });

  it('SUSPENDED → ended', () => {
    expect(offerCardState(makeOffer({ status: 'SUSPENDED' }), now)).toBe('ended');
  });

  it('SCHEDULED·마감 미래 → scheduled', () => {
    expect(
      offerCardState(makeOffer({ status: 'SCHEDULED', salesEnd: minutesFromNow(120) }), now),
    ).toBe('scheduled');
  });

  it('품절이지만 마감이 지남 → ended(우선순위)', () => {
    expect(
      offerCardState(
        makeOffer({ status: 'SOLD_OUT', remainingStock: 0, salesEnd: minutesFromNow(-1) }),
        now,
      ),
    ).toBe('ended');
  });
});

describe('formatPickupWindow', () => {
  const window = (start: Date, end: Date) => makeOffer({ pickupStart: start, pickupEnd: end });

  it('오늘 18:00–20:00 → 오늘 18:00–20:00', () => {
    const o = window(new Date(2026, 10, 10, 18, 0), new Date(2026, 10, 10, 20, 0));
    expect(formatPickupWindow(o, now)).toBe('오늘 18:00–20:00');
  });

  it('내일 → 11/11 18:00–20:00', () => {
    const o = window(new Date(2026, 10, 11, 18, 0), new Date(2026, 10, 11, 20, 0));
    expect(formatPickupWindow(o, now)).toBe('11/11 18:00–20:00');
  });

  it('09:05–10:00은 0을 채운다', () => {
    const o = window(new Date(2026, 10, 10, 9, 5), new Date(2026, 10, 10, 10, 0));
    expect(formatPickupWindow(o, now)).toBe('오늘 09:05–10:00');
  });

  it('23:00–다음 날 01:00은 끝 시각에 날짜를 붙이지 않는다', () => {
    const o = window(new Date(2026, 10, 10, 23, 0), new Date(2026, 10, 11, 1, 0));
    expect(formatPickupWindow(o, now)).toBe('오늘 23:00–01:00');
  });

  it('1월 7일 → 01/07 …', () => {
    const o = window(new Date(2027, 0, 7, 18, 0), new Date(2027, 0, 7, 20, 0));
    expect(formatPickupWindow(o, now)).toBe('01/07 18:00–20:00');
  });

  it('시작이 어제 → 11/09 …', () => {
    const o = window(new Date(2026, 10, 9, 18, 0), new Date(2026, 10, 9, 20, 0));
    expect(formatPickupWindow(o, now)).toBe('11/09 18:00–20:00');
  });
});
