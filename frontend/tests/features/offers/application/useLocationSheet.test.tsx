import { act, waitFor } from '@testing-library/react';
import { useHomeOffers, useLocationSheet } from '@/features/offers';
import { canRefreshLocation, locationStatusLine } from '@/features/offers/domain/locationSheet';
import { FakeLocationProvider, located, unavailable } from '../fakes/fakeLocationProvider.fake';
import { FakeOfferRepository } from '../fakes/fakeOfferRepository.fake';
import { renderOffersHook } from '../../../support/renderWithOffers';

function setup(location = new FakeLocationProvider(located), offers = new FakeOfferRepository()) {
  return renderOffersHook(
    () => {
      const home = useHomeOffers();
      return { home, sheet: useLocationSheet(home) };
    },
    { offerFakes: { offers, location } },
  );
}

const lastQuery = (offers: FakeOfferRepository) => offers.findNearby.mock.calls.at(-1)?.[0];

// open() 뒤 열린 상태인지 함께 확인한다(닫힌 채로 남는 구현이 뒤 단언을 우연히 통과하지 않게).
function openSheet(result: ReturnType<typeof setup>['result']) {
  act(() => result.current.sheet.open());
  expect(result.current.sheet.isOpen).toBe(true);
}

async function settled(result: ReturnType<typeof setup>['result']) {
  await waitFor(() => expect(result.current.home.list.status).toBe('success'));
}

describe('useLocationSheet', () => {
  it('처음에는 닫혀 있고 draftRadiusKm은 3이다', () => {
    const { result } = setup();
    expect(result.current.sheet.isOpen).toBe(false);
    expect(result.current.sheet.draftRadiusKm).toBe(3);
  });

  it('open() → isOpen true, draftRadiusKm은 현재 radiusKm', async () => {
    const { result } = setup();
    await settled(result);
    openSheet(result);
    expect(result.current.sheet.isOpen).toBe(true);
    expect(result.current.sheet.draftRadiusKm).toBe(result.current.home.radiusKm);
  });

  it('selectRadius(5) → draft 5, home.radiusKm 3 그대로, 저장소 호출 수 불변', async () => {
    const { result, offerFakes } = setup();
    await settled(result);
    const calls = offerFakes.offers.findNearby.mock.calls.length;
    openSheet(result);
    act(() => result.current.sheet.selectRadius(5));
    await act(async () => {});
    expect(result.current.sheet.draftRadiusKm).toBe(5);
    expect(result.current.home.radiusKm).toBe(3);
    expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(calls);
  });

  it('selectRadius(25)·selectRadius(NaN) → draft 변화 없음', async () => {
    const { result } = setup();
    await settled(result);
    openSheet(result);
    act(() => result.current.sheet.selectRadius(25));
    expect(result.current.sheet.draftRadiusKm).toBe(3);
    act(() => result.current.sheet.selectRadius(Number.NaN));
    expect(result.current.sheet.draftRadiusKm).toBe(3);
  });

  it('apply() → radiusKm 5, area.radiusKm 5로 재조회, 닫힘, chipLabel 내 주변 · 5km', async () => {
    const { result, offerFakes } = setup();
    await settled(result);
    openSheet(result);
    act(() => result.current.sheet.selectRadius(5));
    act(() => result.current.sheet.apply());
    expect(result.current.home.radiusKm).toBe(5);
    expect(result.current.sheet.isOpen).toBe(false);
    expect(result.current.home.chipLabel).toBe('내 주변 · 5km');
    await waitFor(() =>
      expect(lastQuery(offerFakes.offers)).toMatchObject({ area: { radiusKm: 5 } }),
    );
  });

  it('draft가 현재와 같을 때 apply() → 저장소 추가 호출 0, 닫힘', async () => {
    const { result, offerFakes } = setup();
    await settled(result);
    const calls = offerFakes.offers.findNearby.mock.calls.length;
    openSheet(result);
    act(() => result.current.sheet.apply());
    await act(async () => {});
    expect(result.current.sheet.isOpen).toBe(false);
    expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(calls);
  });

  it('close() → 닫힘, radiusKm 불변, 저장소 호출 불변', async () => {
    const { result, offerFakes } = setup();
    await settled(result);
    const calls = offerFakes.offers.findNearby.mock.calls.length;
    openSheet(result);
    act(() => result.current.sheet.selectRadius(5));
    act(() => result.current.sheet.close());
    await act(async () => {});
    expect(result.current.sheet.isOpen).toBe(false);
    expect(result.current.home.radiusKm).toBe(3);
    expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(calls);
  });

  it('selectRadius(10) 뒤 close(), 다시 open() → draft는 현재 반경(10이 아님)', async () => {
    const { result } = setup();
    await settled(result);
    openSheet(result);
    act(() => result.current.sheet.selectRadius(10));
    act(() => result.current.sheet.close());
    openSheet(result);
    expect(result.current.sheet.draftRadiusKm).toBe(3);
  });

  it('5로 적용한 뒤 open() → draft 5', async () => {
    const { result } = setup();
    await settled(result);
    openSheet(result);
    act(() => result.current.sheet.selectRadius(5));
    act(() => result.current.sheet.apply());
    openSheet(result);
    expect(result.current.sheet.draftRadiusKm).toBe(5);
  });

  it('refreshLocation()(located) → provider 호출 +1, locating → located, isOpen 그대로', async () => {
    const { result, offerFakes } = setup();
    await settled(result);
    const calls = offerFakes.location.current.mock.calls.length;
    openSheet(result);
    act(() => result.current.sheet.refreshLocation());
    expect(offerFakes.location.current).toHaveBeenCalledTimes(calls + 1);
    expect(result.current.home.location.status).toBe('locating');
    await waitFor(() => expect(result.current.home.location.status).toBe('located'));
    expect(result.current.sheet.isOpen).toBe(true);
  });

  it('refreshLocation()(locating 중) → provider 호출 불변, canUseCurrent false', async () => {
    const { result, offerFakes } = setup(new FakeLocationProvider());
    await act(async () => {});
    expect(result.current.home.location.status).toBe('locating');
    const calls = offerFakes.location.current.mock.calls.length;
    openSheet(result);
    act(() => result.current.sheet.refreshLocation());
    expect(offerFakes.location.current).toHaveBeenCalledTimes(calls);
    expect(result.current.sheet.canUseCurrent).toBe(false);
  });

  it('refreshLocation()(unavailable) → provider 다시 호출, 다시 unavailable이어도 isOpen 유지', async () => {
    const { result, offerFakes } = setup(new FakeLocationProvider(unavailable));
    await settled(result);
    const calls = offerFakes.location.current.mock.calls.length;
    openSheet(result);
    act(() => result.current.sheet.refreshLocation());
    expect(offerFakes.location.current).toHaveBeenCalledTimes(calls + 1);
    await waitFor(() => expect(result.current.home.location.status).toBe('unavailable'));
    expect(result.current.sheet.isOpen).toBe(true);
  });

  it('statusLine: located는 domain 문구와 같다', async () => {
    const { result } = setup();
    await settled(result);
    expect(result.current.sheet.statusLine).toBe(locationStatusLine('located'));
    expect(result.current.sheet.canUseCurrent).toBe(canRefreshLocation('located'));
  });

  it('statusLine: locating은 domain 문구와 같다', async () => {
    const { result } = setup(new FakeLocationProvider());
    await act(async () => {});
    expect(result.current.sheet.statusLine).toBe(locationStatusLine('locating'));
  });

  it('statusLine: unavailable은 domain 문구와 같다', async () => {
    const { result } = setup(new FakeLocationProvider(unavailable));
    await settled(result);
    expect(result.current.sheet.statusLine).toBe(locationStatusLine('unavailable'));
  });

  it('selectRadius(5) 뒤 refreshLocation() → draft 5 유지', async () => {
    const { result } = setup();
    await settled(result);
    openSheet(result);
    act(() => result.current.sheet.selectRadius(5));
    act(() => result.current.sheet.refreshLocation());
    await waitFor(() => expect(result.current.home.location.status).toBe('located'));
    expect(result.current.sheet.draftRadiusKm).toBe(5);
  });

  it('위치 확인 중 apply() → 반경 반영, 위치가 확정되면 그 반경으로 조회한다', async () => {
    const location = new FakeLocationProvider();
    const { result, offerFakes } = setup(location);
    await act(async () => {});
    openSheet(result);
    act(() => result.current.sheet.selectRadius(5));
    act(() => result.current.sheet.apply());
    expect(result.current.home.radiusKm).toBe(5);
    expect(offerFakes.offers.findNearby).not.toHaveBeenCalled();
    await act(async () => location.resolve(located));
    await waitFor(() =>
      expect(lastQuery(offerFakes.offers)).toMatchObject({ area: { radiusKm: 5 } }),
    );
  });

  it('위치 unavailable에서 apply() → radiusKm 반영, 조회 area null 그대로(재조회 없음)', async () => {
    const { result, offerFakes } = setup(new FakeLocationProvider(unavailable));
    await settled(result);
    const calls = offerFakes.offers.findNearby.mock.calls.length;
    openSheet(result);
    act(() => result.current.sheet.selectRadius(5));
    act(() => result.current.sheet.apply());
    await act(async () => {});
    expect(result.current.home.radiusKm).toBe(5);
    expect(lastQuery(offerFakes.offers)).toMatchObject({ area: null });
    expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(calls);
  });
});
