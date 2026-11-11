import {
  formatDistance,
  pickupWindow,
  salesCountdown,
  toOfferCardView,
} from '@/features/offers/domain/offerFormat';
import { NOW, at } from '../../../support/clock';
import { makeNearby } from '../fakes/offers';

const plus = (ms: number) => new Date(NOW.getTime() + ms);
const MIN = 60_000;

describe('salesCountdown', () => {
  it.each<[string, number, string | null]>([
    ['42분', 42 * MIN, '판매 마감 42분 전'],
    ['30초(1분 미만은 올림)', 30_000, '판매 마감 1분 전'],
    ['59분 30초(올림해 60분)', 59 * MIN + 30_000, '판매 마감 1시간 전'],
    ['60분(정각)', 60 * MIN, '판매 마감 1시간 전'],
    ['70분', 70 * MIN, '판매 마감 1시간 10분 전'],
    ['25시간 3분(24시간 이상도 시간)', (25 * 60 + 3) * MIN, '판매 마감 25시간 3분 전'],
    ['0(마감 시각 정각)', 0, null],
    ['−1분(지남)', -MIN, null],
  ])('%s → %j', (_name, diff, expected) => {
    expect(salesCountdown(plus(diff), NOW)).toBe(expected);
  });
});

describe('pickupWindow', () => {
  it('오늘이면 「오늘 18:00–20:00」(en dash U+2013)', () => {
    const text = pickupWindow(at(10, 18, 0), at(10, 20, 0), NOW);
    expect(text).toBe('오늘 18:00–20:00');
  });

  it('다음 날이면 「내일 …」', () => {
    expect(pickupWindow(at(11, 9, 0), at(11, 10, 30), NOW)).toBe('내일 09:00–10:30');
  });

  it('모레 이후면 MM/DD', () => {
    expect(pickupWindow(at(12, 18, 0), at(12, 20, 0), NOW)).toBe('11/12 18:00–20:00');
  });
});

describe('formatDistance', () => {
  it.each<[number | null, string | null]>([
    [null, null],
    [0.42, '0.4km'],
    [0.03, '0.1km'],
    [12, '12.0km'],
  ])('%j → %j', (km, expected) => {
    expect(formatDistance(km)).toBe(expected);
  });
});

describe('toOfferCardView', () => {
  it('거리가 있으면 storeLine에 거리, 가격·할인율 표기', () => {
    const view = toOfferCardView(makeNearby({}, 0.42), NOW);
    expect(view).toMatchObject({
      storeLine: '망원베이커리 · 0.4km',
      title: '소금빵 세트',
      salePrice: '6,000원',
      originalPrice: '12,000',
      rate: '50%',
      pickup: '오늘 18:00–20:00',
      countdown: '판매 마감 42분 전',
      remaining: '남은 3개',
      soldOut: false,
      ended: false,
    });
  });

  it('품절(remainingStock 0)이면 soldOut, countdown·remaining은 null', () => {
    const view = toOfferCardView(makeNearby({ remainingStock: 0 }), NOW);
    expect(view.soldOut).toBe(true);
    expect(view.countdown).toBeNull();
    expect(view.remaining).toBeNull();
    expect(view.storeLine).toBe('망원베이커리');
  });

  it('salesEnd가 지났으면 ended: true, countdown null', () => {
    const view = toOfferCardView(makeNearby({ salesEnd: at(10, 17, 0) }), NOW);
    expect(view.ended).toBe(true);
    expect(view.countdown).toBeNull();
  });
});
