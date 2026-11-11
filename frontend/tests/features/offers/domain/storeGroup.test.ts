import { groupByStore, storeOfferCountText } from '@/features/offers';
import { at } from '../../../support/clock';
import { makeNearby } from '../fakes/offers';

const a1 = makeNearby(
  { id: 'a1', storeId: 'sa', storeName: '가게A', salesEnd: at(10, 19, 0) },
  0.8,
);
const b1 = makeNearby(
  { id: 'b1', storeId: 'sb', storeName: '가게B', salesEnd: at(10, 18, 0) },
  1.2,
);
const a2 = makeNearby(
  { id: 'a2', storeId: 'sa', storeName: '가게A', salesEnd: at(10, 18, 30) },
  0.5,
);

describe('groupByStore', () => {
  it('빈 배열 → []', () => {
    expect(groupByStore([])).toEqual([]);
  });

  it('처음 나온 가게 순서, 가게 안 순서 유지', () => {
    const groups = groupByStore([a1, b1, a2]);
    expect(groups.map((g) => g.storeId)).toEqual(['sa', 'sb']);
    expect(groups.map((g) => g.storeName)).toEqual(['가게A', '가게B']);
    expect(groups[0]!.offers.map((o) => o.offer.id)).toEqual(['a1', 'a2']);
    expect(groups[1]!.offers.map((o) => o.offer.id)).toEqual(['b1']);
  });

  it('distanceKm는 null 아닌 최솟값, earliestSalesEnd는 최소 salesEnd', () => {
    const nullFirst = makeNearby(
      { id: 'a0', storeId: 'sa', storeName: '가게A', salesEnd: at(10, 20, 0) },
      null,
    );
    const [ga] = groupByStore([nullFirst, a1, a2]);
    expect(ga!.distanceKm).toBe(0.5);
    expect(ga!.earliestSalesEnd.getTime()).toBe(at(10, 18, 30).getTime());
  });

  it('모두 null이면 distanceKm null', () => {
    const x = makeNearby({ id: 'x1', storeId: 'sx' }, null);
    const y = makeNearby({ id: 'x2', storeId: 'sx' }, null);
    expect(groupByStore([x, y])[0]!.distanceKm).toBeNull();
  });
});

describe('storeOfferCountText', () => {
  it.each([
    [1, '할인 1개'],
    [3, '할인 3개'],
  ])('%i → %s', (n, text) => {
    expect(storeOfferCountText(n)).toBe(text);
  });
});
