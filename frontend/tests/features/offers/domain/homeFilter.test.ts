import {
  DEFAULT_HOME_FILTER,
  effectiveSort,
  isSortAvailable,
  locationChipLabel,
  nextRadius,
  readHomeFilter,
  toHomeSearch,
  type HomeFilter,
} from '@/features/offers/domain/homeFilter';

describe('readHomeFilter', () => {
  it("'' → 기본값", () => {
    expect(readHomeFilter('')).toEqual(DEFAULT_HOME_FILTER);
    expect(DEFAULT_HOME_FILTER).toEqual({ sort: 'sales_end', radiusKm: 3, keyword: '' });
  });

  it('?sort=price&radius=5&q=%20빵%20 → {price, 5, 빵}', () => {
    expect(readHomeFilter('?sort=price&radius=5&q=%20%EB%B9%B5%20')).toEqual({
      sort: 'price',
      radiusKm: 5,
      keyword: '빵',
    });
  });

  it('모르는 sort·radius는 기본값(sales_end, 3)', () => {
    expect(readHomeFilter('?sort=x&radius=7')).toEqual({
      sort: 'sales_end',
      radiusKm: 3,
      keyword: '',
    });
  });

  it('q가 101자면 앞 100자', () => {
    const q = 'a'.repeat(101);
    expect(readHomeFilter(`?q=${q}`).keyword).toBe('a'.repeat(100));
  });
});

describe('toHomeSearch', () => {
  it("기본값 → ''", () => {
    expect(toHomeSearch(DEFAULT_HOME_FILTER)).toBe('');
  });

  it('{distance, 10, 빵} → ?sort=distance&radius=10&q=빵, 왕복하면 같은 값', () => {
    const filter: HomeFilter = { sort: 'distance', radiusKm: 10, keyword: '빵' };
    const search = toHomeSearch(filter);
    expect(new URLSearchParams(search).toString()).toBe(
      new URLSearchParams('?sort=distance&radius=10&q=빵').toString(),
    );
    expect(search.startsWith('?')).toBe(true);
    expect(readHomeFilter(search)).toEqual(filter);
  });
});

describe('isSortAvailable·effectiveSort', () => {
  it("effectiveSort('distance', 위치 없음) → sales_end", () => {
    expect(effectiveSort('distance', false)).toBe('sales_end');
  });

  it("effectiveSort('distance', 위치 있음) → distance", () => {
    expect(effectiveSort('distance', true)).toBe('distance');
  });

  it("isSortAvailable('price', 위치 없음) → true", () => {
    expect(isSortAvailable('price', false)).toBe(true);
  });
});

describe('nextRadius', () => {
  it('3 → 5', () => {
    expect(nextRadius(3)).toBe(5);
  });

  it('10 → null', () => {
    expect(nextRadius(10)).toBeNull();
  });
});

describe('locationChipLabel', () => {
  it('위치 있음 「현재 위치 · 3km」 / 없음 「전체 지역」', () => {
    expect(locationChipLabel(true, 3)).toBe('현재 위치 · 3km');
    expect(locationChipLabel(false, 3)).toBe('전체 지역');
  });
});
