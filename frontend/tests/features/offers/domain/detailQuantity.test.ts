import { detailReturnPath, readQuantityParam } from '@/features/offers';

describe('readQuantityParam', () => {
  it.each<[string, number]>([
    ['?qty=2', 2],
    ['?qty=5', 5],
    ['?qty=9', 9],
  ])('%s → %d(상한으로 자르지 않음)', (search, n) => {
    expect(readQuantityParam(search)).toBe(n);
  });

  it.each([['?qty=0'], ['?qty=-1'], ['?qty=abc'], ['?qty=1.5'], ['?qty='], [''], ['?other=1']])(
    '%j → null',
    (search) => {
      expect(readQuantityParam(search)).toBeNull();
    },
  );
});

describe('detailReturnPath', () => {
  it("('/offers/abc', 3) → '/offers/abc?qty=3'", () => {
    expect(detailReturnPath('/offers/abc', 3)).toBe('/offers/abc?qty=3');
  });
});
