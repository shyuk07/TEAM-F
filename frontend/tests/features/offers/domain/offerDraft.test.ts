import {
  defaultDraft,
  applyQuickPick,
  isCancelBlocked,
  validateDraft,
  toCreateInput,
  type OfferDraft,
} from '@/features/offers';

// 시간대와 관계없이 같은 순간을 쓰도록 KST 오프셋을 명시한다.
const NOW = new Date('2026-11-04T17:30:00+09:00');
const MIN = 60_000;

function draft(over: Partial<OfferDraft> = {}): OfferDraft {
  return defaultDraft(NOW, {
    productId: 'p1',
    salePrice: 6000,
    initialStock: 10,
    ...over,
  });
}

const validDraft = (over: Partial<OfferDraft> = {}) =>
  draft({
    salesEnd: new Date(NOW.getTime() + 120 * MIN),
    pickupStart: new Date(NOW.getTime() + 120 * MIN),
    pickupEnd: new Date(NOW.getTime() + 240 * MIN),
    ...over,
  });

describe('validateDraft', () => {
  it('판매가가 정가와 같으면 price-gte-original 이슈', () => {
    expect(validateDraft(validDraft(), 6000, NOW)).toContain('price-gte-original');
  });
  it('판매가가 정가보다 크면 price-gte-original 이슈', () => {
    expect(validateDraft(validDraft(), 5000, NOW)).toContain('price-gte-original');
  });
  it('판매가가 정가보다 1원 작으면 유효 (가격 이슈 없음)', () => {
    const issues = validateDraft(validDraft(), 6001, NOW);
    expect(issues).not.toContain('price-gte-original');
    expect(issues).toEqual([]);
  });
  it('판매가가 0 이하면 price-zero-or-less 이슈', () => {
    expect(validateDraft(validDraft({ salePrice: 0 }), 6000, NOW)).toContain('price-zero-or-less');
    expect(validateDraft(validDraft({ salePrice: -100 }), 6000, NOW)).toContain('price-zero-or-less');
  });
  it('최초 수량 0은 거절, 1과 9999는 허용, 10000은 거절', () => {
    expect(validateDraft(validDraft({ initialStock: 0 }), 6001, NOW)).toContain('stock-zero-or-less');
    expect(validateDraft(validDraft({ initialStock: 1 }), 6001, NOW)).toEqual([]);
    expect(validateDraft(validDraft({ initialStock: 9999 }), 6001, NOW)).toEqual([]);
    expect(validateDraft(validDraft({ initialStock: 10000 }), 6001, NOW)).toContain('stock-over-max');
  });
  it('판매 마감이 판매 시작 이하면 sales-end-before-start 이슈', () => {
    const salesEnd = new Date(NOW.getTime()); // salesStart 'now' = NOW
    expect(validateDraft(draft({ salesEnd, pickupStart: salesEnd, pickupEnd: new Date(salesEnd.getTime() + MIN) }), 6000, NOW)).toContain('sales-end-before-start');
  });
  it('픽업 마감이 판매 마감 이하면 pickup-end-before-sales-end 이슈', () => {
    const pickupStart = new Date(NOW.getTime() + 120 * MIN);
    const salesEnd = pickupStart;
    expect(validateDraft(draft({ salesEnd, pickupStart, pickupEnd: salesEnd }), 6000, NOW)).toContain('pickup-end-before-sales-end');
  });
  it('픽업 마감이 픽업 시작 이하면 pickup-end-before-pickup-start 이슈', () => {
    const pickupStart = new Date(NOW.getTime() + 120 * MIN);
    expect(validateDraft(draft({ salesEnd: new Date(pickupStart.getTime() + MIN), pickupStart, pickupEnd: pickupStart }), 6000, NOW)).toContain('pickup-end-before-pickup-start');
  });
});

describe('isCancelBlocked', () => {
  it('픽업 시작까지 60분 남으면 취소 불가 (정각 포함)', () => {
    const d = draft({ pickupStart: new Date(NOW.getTime() + 60 * MIN) });
    expect(isCancelBlocked(d, NOW)).toBe(true);
  });
  it('픽업 시작까지 61분 이상 남으면 취소 가능', () => {
    const d = draft({ pickupStart: new Date(NOW.getTime() + 61 * MIN) });
    expect(isCancelBlocked(d, NOW)).toBe(false);
  });
});

describe('applyQuickPick', () => {
  it.each([30, 60, 120, 180])('%d분 후 빠른 선택 시 pickupStart·salesEnd·pickupEnd 갱신', (minutes) => {
    const base = draft();
    const next = applyQuickPick(base, minutes, NOW);

    const pickupStart = new Date(NOW.getTime() + minutes * MIN);
    expect(next.pickupStart.getTime()).toBe(pickupStart.getTime());
    expect(next.salesEnd.getTime()).toBe(pickupStart.getTime());
    expect(next.pickupEnd.getTime()).toBe(pickupStart.getTime() + 120 * MIN);
    expect(next.salesStart).toBe('now');
    expect(next.quickPick).toBe(minutes);
  });
});

describe('toCreateInput', () => {
  it("salesStart가 'now'이면 sales_start에 해당하는 salesStart 키가 생략된다(undefined)", () => {
    const input = toCreateInput(validDraft());
    expect(input.salesStart).toBeUndefined();
    expect('salesStart' in input).toBe(true); // 키는 있으나 undefined
    expect(input.salesEnd).toEqual(validDraft().salesEnd);
    expect(input.pickupStart).toEqual(validDraft().pickupStart);
    expect(input.pickupEnd).toEqual(validDraft().pickupEnd);
  });
  it('salesStart가 날짜면 그대로 전달된다', () => {
    const at = new Date('2026-11-05T09:00:00+09:00');
    const input = toCreateInput(validDraft({ salesStart: at }));
    expect(input.salesStart).toEqual(at);
  });
});
