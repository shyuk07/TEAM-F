import { act, waitFor } from '@testing-library/react';
import { useCurrentLocation } from '@/features/offers/application/useCurrentLocation';
import { FakeLocationProvider, located, unavailable } from '../fakes/fakeLocationProvider.fake';
import { FakeOfferRepository } from '../fakes/fakeOfferRepository.fake';
import { renderOffersHook } from '../../../support/renderWithOffers';

function setup(location = new FakeLocationProvider()) {
  return renderOffersHook(() => useCurrentLocation(), {
    offerFakes: { offers: new FakeOfferRepository(), location },
  });
}

describe('useCurrentLocation', () => {
  it('처음에는 locating, point 없음, 포트를 한 번 부른다', () => {
    const { result, offerFakes } = setup();
    expect(result.current.status).toBe('locating');
    expect(result.current.point).toBeNull();
    expect(offerFakes.location.current).toHaveBeenCalledTimes(1);
  });

  it('성공하면 located와 point', async () => {
    const { result, offerFakes } = setup();
    await act(async () => offerFakes.location.resolve(located));
    expect(result.current.status).toBe('located');
    expect(result.current.point).toEqual({ lat: 37.5, lng: 126.9 });
  });

  it('unavailable 결과면 unavailable', async () => {
    const { result, offerFakes } = setup();
    await act(async () => offerFakes.location.resolve(unavailable));
    expect(result.current.status).toBe('unavailable');
    expect(result.current.point).toBeNull();
  });

  it('포트가 예외를 던져도 unavailable', async () => {
    const location = new FakeLocationProvider();
    location.current.mockRejectedValue(new Error('geo'));
    const { result } = setup(location);
    await waitFor(() => expect(result.current.status).toBe('unavailable'));
  });

  it('retry()는 locating을 거쳐 다시 요청한다', async () => {
    const { result, offerFakes } = setup();
    await act(async () => offerFakes.location.resolve(unavailable));
    expect(result.current.status).toBe('unavailable');
    act(() => result.current.retry());
    expect(result.current.status).toBe('locating');
    expect(offerFakes.location.current).toHaveBeenCalledTimes(2);
    await act(async () => offerFakes.location.resolve(located));
    expect(result.current.status).toBe('located');
  });

  it('언마운트 뒤 늦은 결과로 상태가 바뀌지 않는다', async () => {
    const { result, unmount, offerFakes } = setup();
    unmount();
    await act(async () => offerFakes.location.resolve(located));
    expect(result.current.status).toBe('locating');
    expect(result.current.point).toBeNull();
  });
});
