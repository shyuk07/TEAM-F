import { act, waitFor } from '@testing-library/react';
import { useDeviceLocation } from '@/features/offers';
import type { GeoPoint } from '@/features/offers';
import { anonymousFakes } from '../../../support/authFakes';
import { deferred } from '../../auth/fakes/deferred';
import { MANGWON } from '../fakes/fakeLocationProvider.fake';
import { renderOffersHook } from './renderOffersHook';

describe('useDeviceLocation', () => {
  it('처음은 pending, 좌표를 받으면 ok와 point', async () => {
    const fakes = anonymousFakes();
    const d = deferred<GeoPoint | null>();
    fakes.location.current.mockReturnValue(d.promise);
    const { result } = renderOffersHook(() => useDeviceLocation(), { fakes });
    expect(result.current.status).toBe('pending');
    expect(result.current.point).toBeNull();
    await act(async () => d.resolve(MANGWON));
    expect(result.current.status).toBe('ok');
    expect(result.current.point).toEqual(MANGWON);
  });

  it('null을 받으면 unavailable', async () => {
    const { result, fakes } = renderOffersHook(() => useDeviceLocation());
    await waitFor(() => expect(result.current.status).toBe('unavailable'));
    expect(result.current.point).toBeNull();
    expect(fakes.location.current).toHaveBeenCalledTimes(1);
  });

  it('request()는 pending을 거쳐 다시 요청하고 ok가 된다', async () => {
    const { result, fakes } = renderOffersHook(() => useDeviceLocation());
    await waitFor(() => expect(result.current.status).toBe('unavailable'));
    const d = deferred<GeoPoint | null>();
    fakes.location.current.mockReturnValueOnce(d.promise);
    act(() => result.current.request());
    expect(result.current.status).toBe('pending');
    expect(fakes.location.current).toHaveBeenCalledTimes(2);
    await act(async () => d.resolve(MANGWON));
    expect(result.current.status).toBe('ok');
    expect(result.current.point).toEqual(MANGWON);
  });
});
