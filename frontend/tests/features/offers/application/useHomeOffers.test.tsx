import { act, waitFor } from '@testing-library/react';
import { useHomeOffers } from '@/features/offers';
import { pageOf } from '../fakes/offers';
import { FakeLocationProvider, located, unavailable } from '../fakes/fakeLocationProvider.fake';
import { FakeOfferRepository } from '../fakes/fakeOfferRepository.fake';
import { renderOffersHook } from '../../../support/renderWithOffers';

function setup(location = new FakeLocationProvider(), offers = new FakeOfferRepository()) {
  return renderOffersHook(() => useHomeOffers(), { offerFakes: { offers, location } });
}

const lastQuery = (offers: FakeOfferRepository) => offers.findNearby.mock.calls.at(-1)?.[0];

describe('useHomeOffers', () => {
  it('위치 locating 동안 목록은 loading이고 저장소를 부르지 않는다', async () => {
    const { result, offerFakes } = setup();
    await act(async () => {});
    expect(result.current.location.status).toBe('locating');
    expect(result.current.list.status).toBe('loading');
    expect(offerFakes.offers.findNearby).not.toHaveBeenCalled();
  });

  it('위치 located → area {point, radiusKm: 3}, sort sales_end로 조회한다', async () => {
    const { result, offerFakes } = setup(new FakeLocationProvider(located));
    await waitFor(() => expect(result.current.list.status).toBe('success'));
    expect(lastQuery(offerFakes.offers)).toMatchObject({
      area: { point: { lat: 37.5, lng: 126.9 }, radiusKm: 3 },
      sort: 'sales_end',
      keyword: undefined,
    });
    expect(result.current.hasLocation).toBe(true);
  });

  it('위치 unavailable → area null, hasLocation false', async () => {
    const { result, offerFakes } = setup(new FakeLocationProvider(unavailable));
    await waitFor(() => expect(result.current.list.status).toBe('success'));
    expect(lastQuery(offerFakes.offers)).toMatchObject({ area: null });
    expect(result.current.hasLocation).toBe(false);
    expect(result.current.location.status).toBe('unavailable');
  });

  it('selectSort(distance): 위치 있음 → distance로 재조회', async () => {
    const { result, offerFakes } = setup(new FakeLocationProvider(located));
    await waitFor(() => expect(result.current.list.status).toBe('success'));
    act(() => result.current.selectSort('distance'));
    expect(result.current.sort).toBe('distance');
    await waitFor(() => expect(lastQuery(offerFakes.offers)).toMatchObject({ sort: 'distance' }));
  });

  it('selectSort(distance): 위치 없음 → 상태·호출 변화 없음', async () => {
    const { result, offerFakes } = setup(new FakeLocationProvider(unavailable));
    await waitFor(() => expect(result.current.list.status).toBe('success'));
    const calls = offerFakes.offers.findNearby.mock.calls.length;
    act(() => result.current.selectSort('distance'));
    await act(async () => {});
    expect(result.current.sort).toBe('sales_end');
    expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(calls);
  });

  it('위치가 있다가 retry()로 unavailable이 되면 선택한 distance 대신 sales_end를 돌려준다', async () => {
    const location = new FakeLocationProvider(located);
    const { result } = setup(location);
    await waitFor(() => expect(result.current.list.status).toBe('success'));
    act(() => result.current.selectSort('distance'));
    expect(result.current.sort).toBe('distance');
    location.result = unavailable;
    act(() => result.current.location.retry());
    await waitFor(() => expect(result.current.location.status).toBe('unavailable'));
    expect(result.current.sort).toBe('sales_end');
  });

  it("submitKeyword('  빵 ') → keyword '빵'으로 재조회", async () => {
    const { result, offerFakes } = setup(new FakeLocationProvider(located));
    await waitFor(() => expect(result.current.list.status).toBe('success'));
    act(() => result.current.submitKeyword('  빵 '));
    expect(result.current.keyword).toBe('빵');
    await waitFor(() => expect(lastQuery(offerFakes.offers)).toMatchObject({ keyword: '빵' }));
  });

  it("submitKeyword('   ') → 검색어를 지운다", async () => {
    const { result, offerFakes } = setup(new FakeLocationProvider(located));
    await waitFor(() => expect(result.current.list.status).toBe('success'));
    act(() => result.current.submitKeyword('빵'));
    await waitFor(() => expect(lastQuery(offerFakes.offers)).toMatchObject({ keyword: '빵' }));
    act(() => result.current.submitKeyword('   '));
    expect(result.current.keyword).toBeUndefined();
    await waitFor(() => expect(lastQuery(offerFakes.offers)?.keyword).toBeUndefined());
  });

  it('runEmptyAction(widenRadius) → radiusKm 5로 재조회, chipLabel 내 주변 · 5km', async () => {
    const offers = new FakeOfferRepository();
    offers.findNearby.mockResolvedValue(pageOf([]));
    const { result } = setup(new FakeLocationProvider(located), offers);
    await waitFor(() => expect(result.current.list.status).toBe('empty'));
    expect(result.current.empty.action).toBe('widenRadius');
    act(() => result.current.runEmptyAction());
    expect(result.current.radiusKm).toBe(5);
    expect(result.current.chipLabel).toBe('내 주변 · 5km');
    await waitFor(() => expect(lastQuery(offers)).toMatchObject({ area: { radiusKm: 5 } }));
  });

  it('runEmptyAction(clearKeyword) → 검색어를 지운다', async () => {
    const offers = new FakeOfferRepository();
    offers.findNearby.mockResolvedValue(pageOf([]));
    const { result } = setup(new FakeLocationProvider(located), offers);
    await waitFor(() => expect(result.current.list.status).toBe('empty'));
    act(() => result.current.submitKeyword('빵'));
    await waitFor(() => expect(result.current.empty.action).toBe('clearKeyword'));
    act(() => result.current.runEmptyAction());
    expect(result.current.keyword).toBeUndefined();
  });

  it('chipLabel: 위치 확인 중 → 내 주변 · 3km', async () => {
    const location = new FakeLocationProvider();
    const { result } = setup(location);
    expect(result.current.chipLabel).toBe('위치 확인 중');
    await act(async () => location.resolve(located));
    expect(result.current.chipLabel).toBe('내 주변 · 3km');
  });

  it('chipLabel: 위치 없음', async () => {
    const { result } = setup(new FakeLocationProvider(unavailable));
    await waitFor(() => expect(result.current.chipLabel).toBe('위치 없음'));
  });

  it('setRadiusKm(10) → radiusKm 10, area.radiusKm 10으로 재조회, chipLabel 내 주변 · 10km', async () => {
    const { result, offerFakes } = setup(new FakeLocationProvider(located));
    await waitFor(() => expect(result.current.list.status).toBe('success'));
    act(() => result.current.setRadiusKm(10));
    expect(result.current.radiusKm).toBe(10);
    expect(result.current.chipLabel).toBe('내 주변 · 10km');
    await waitFor(() =>
      expect(lastQuery(offerFakes.offers)).toMatchObject({ area: { radiusKm: 10 } }),
    );
  });

  it.each([0.1, 20])('setRadiusKm(%s) → 경계값도 반영한다', async (km) => {
    const { result, offerFakes } = setup(new FakeLocationProvider(located));
    await waitFor(() => expect(result.current.list.status).toBe('success'));
    act(() => result.current.setRadiusKm(km));
    expect(result.current.radiusKm).toBe(km);
    await waitFor(() =>
      expect(lastQuery(offerFakes.offers)).toMatchObject({ area: { radiusKm: km } }),
    );
  });

  it.each([0.09, 20.1, Number.NaN])('setRadiusKm(%s) → 상태·재조회 변화 없음', async (km) => {
    const { result, offerFakes } = setup(new FakeLocationProvider(located));
    await waitFor(() => expect(result.current.list.status).toBe('success'));
    const calls = offerFakes.offers.findNearby.mock.calls.length;
    act(() => result.current.setRadiusKm(km));
    await act(async () => {});
    expect(result.current.radiusKm).toBe(3);
    expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(calls);
  });
});
