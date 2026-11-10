import { emptyView } from '@/features/offers/domain/offerEmpty';

describe('emptyView', () => {
  it('검색어 없음·위치 있음·반경 3 → 반경 넓히기', () => {
    expect(emptyView({ keyword: undefined, hasLocation: true, radiusKm: 3 })).toEqual({
      title: '근처에 마감 할인이 없어요',
      reason: '반경을 넓히거나 저녁 시간에 다시 확인해 보세요.',
      action: 'widenRadius',
      actionLabel: '반경 5km로 넓히기',
    });
  });

  it('반경이 5 이상이면 action이 없다', () => {
    const v = emptyView({ keyword: undefined, hasLocation: true, radiusKm: 5 });
    expect(v.title).toBe('근처에 마감 할인이 없어요');
    expect(v.action).toBeNull();
    expect(v.actionLabel).toBeNull();
  });

  it('위치가 없으면 반경이 적용되지 않으므로 action이 없다', () => {
    const v = emptyView({ keyword: undefined, hasLocation: false, radiusKm: 3 });
    expect(v.action).toBeNull();
    expect(v.actionLabel).toBeNull();
  });

  it('검색어가 있으면 검색어 지우기', () => {
    expect(emptyView({ keyword: '빵', hasLocation: false, radiusKm: 3 })).toEqual({
      title: '검색 결과가 없어요',
      reason: '다른 상품명으로 검색해 보세요.',
      action: 'clearKeyword',
      actionLabel: '검색어 지우기',
    });
  });

  it('검색어와 위치가 모두 있으면 검색어가 우선한다', () => {
    const v = emptyView({ keyword: '빵', hasLocation: true, radiusKm: 3 });
    expect(v.action).toBe('clearKeyword');
    expect(v.actionLabel).toBe('검색어 지우기');
  });
});
