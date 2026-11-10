import {
  SORT_CHIPS,
  appendPage,
  hasNextPage,
  isSortSelectable,
  locationChipLabel,
  normalizeKeyword,
  queryKey,
  resolveSort,
  type NearbyOfferQuery,
} from '@/features/offers/domain/search';
import { makeOffer, manyOffers, nearby, pageOf } from '../fakes/offers';

describe('resolveSort', () => {
  it.each([
    ['distance', false, 'sales_end'],
    ['distance', true, 'distance'],
    ['price', false, 'price'],
    ['sales_end', false, 'sales_end'],
  ] as const)('(%s, 위치 %s) → %s', (key, hasLocation, expected) => {
    expect(resolveSort(key, hasLocation)).toBe(expected);
  });
});

describe('isSortSelectable', () => {
  it.each([
    ['distance', false, false],
    ['distance', true, true],
    ['discount_rate', false, true],
  ] as const)('(%s, 위치 %s) → %s', (key, hasLocation, expected) => {
    expect(isSortSelectable(key, hasLocation)).toBe(expected);
  });
});

describe('normalizeKeyword', () => {
  it('앞뒤 공백을 지운다', () => {
    expect(normalizeKeyword('  빵 ')).toBe('빵');
  });

  it('공백만 있으면 undefined', () => {
    expect(normalizeKeyword('   ')).toBeUndefined();
  });

  it('빈 문자열이면 undefined', () => {
    expect(normalizeKeyword('')).toBeUndefined();
  });

  it('100자는 그대로', () => {
    const s = '가'.repeat(100);
    expect(normalizeKeyword(s)).toBe(s);
  });

  it('101자는 100자로 자른다', () => {
    expect(normalizeKeyword('가'.repeat(101))).toBe('가'.repeat(100));
  });

  it('안쪽 공백은 유지한다', () => {
    expect(normalizeKeyword('식빵 모둠')).toBe('식빵 모둠');
  });
});

describe('queryKey', () => {
  const base: Omit<NearbyOfferQuery, 'page'> = {
    area: { point: { lat: 37.5, lng: 126.9 }, radiusKm: 3 },
    keyword: undefined,
    sort: 'sales_end',
    size: 20,
  };

  it('같은 조건이면 같은 키', () => {
    expect(queryKey({ ...base })).toBe(
      queryKey({ ...base, area: { point: { lat: 37.5, lng: 126.9 }, radiusKm: 3 } }),
    );
  });

  it('radiusKm만 다르면 다른 키', () => {
    expect(queryKey({ ...base, area: { point: { lat: 37.5, lng: 126.9 }, radiusKm: 5 } })).not.toBe(
      queryKey(base),
    );
  });

  it('sort만 다르면 다른 키', () => {
    expect(queryKey({ ...base, sort: 'price' })).not.toBe(queryKey(base));
  });

  it('area null과 위치 있음은 다른 키', () => {
    expect(queryKey({ ...base, area: null })).not.toBe(queryKey(base));
  });
});

describe('hasNextPage', () => {
  it.each([
    [1, 20, 21, true],
    [1, 20, 20, false],
    [1, 20, 0, false],
    [2, 20, 40, false],
  ])('(page %i, size %i, total %i) → %s', (page, size, total, expected) => {
    expect(hasNextPage(pageOf([], page, size, total))).toBe(expected);
  });
});

describe('appendPage', () => {
  it('겹치지 않으면 뒤에 붙는다', () => {
    const prev = manyOffers(2, 'a');
    const next = manyOffers(2, 'b');
    expect(appendPage(prev, next)).toEqual([...prev, ...next]);
  });

  it('같은 offer.id는 앞쪽을 유지하고 중복을 뺀다', () => {
    const prev = [nearby(makeOffer({ id: 'x', productName: '앞' }), 0.1)];
    const next = [
      nearby(makeOffer({ id: 'x', productName: '뒤' }), 0.2),
      nearby(makeOffer({ id: 'y' }), 0.3),
    ];
    const merged = appendPage(prev, next);
    expect(merged.map((i) => i.offer.id)).toEqual(['x', 'y']);
    expect(merged[0].offer.productName).toBe('앞');
  });

  it('next가 비어 있으면 그대로', () => {
    const prev = manyOffers(2, 'a');
    expect(appendPage(prev, [])).toEqual(prev);
  });
});

describe('locationChipLabel', () => {
  it.each([
    ['located', 3, '내 주변 · 3km'],
    ['located', 0.5, '내 주변 · 0.5km'],
    ['locating', 3, '위치 확인 중'],
    ['unavailable', 3, '위치 없음'],
  ] as const)('(%s, %f) → %s', (status, radiusKm, expected) => {
    expect(locationChipLabel(status, radiusKm)).toBe(expected);
  });
});

describe('SORT_CHIPS', () => {
  it('순서·라벨·서버 정렬 값', () => {
    expect(SORT_CHIPS).toEqual([
      { key: 'sales_end', label: '마감 임박' },
      { key: 'distance', label: '가까운 순' },
      { key: 'discount_rate', label: '할인율' },
      { key: 'price', label: '낮은 가격' },
    ]);
  });
});
