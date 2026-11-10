import { act, waitFor } from '@testing-library/react';
import { useNearbyOffers, type GeoPoint, type HomeFilter, type OfferPage } from '@/features/offers';
import { ApiError } from '@/shared/api/error';
import { anonymousFakes, type AuthFakes } from '../../../support/authFakes';
import { deferred } from '../../auth/fakes/deferred';
import { MANGWON } from '../fakes/fakeLocationProvider.fake';
import { makeNearbyList, makeOfferPage } from '../fakes/offers';
import { renderOffersHook } from './renderOffersHook';

type Props = { filter: HomeFilter; location: GeoPoint | null; ready: boolean };

const BASE: HomeFilter = { sort: 'sales_end', radiusKm: 3, keyword: '' };

function setup(initialProps: Props, fakes: AuthFakes = anonymousFakes()) {
  return renderOffersHook((p: Props) => useNearbyOffers(p.filter, p.location, p.ready), {
    fakes,
    initialProps,
  });
}

const lastQuery = (fakes: AuthFakes) => fakes.offers.findNearby.mock.calls.at(-1)?.[0];

describe('useNearbyOffers', () => {
  it('ready=false면 요청하지 않고 loading', () => {
    const { result, fakes } = setup({ filter: BASE, location: null, ready: false });
    expect(result.current.status).toBe('loading');
    expect(fakes.offers.findNearby).not.toHaveBeenCalled();
  });

  it('ready가 되면 첫 페이지 쿼리로 요청하고 success', async () => {
    const fakes = anonymousFakes();
    fakes.offers.findNearby.mockResolvedValue(makeOfferPage(makeNearbyList(2)));
    const { result, rerender } = setup({ filter: BASE, location: null, ready: false }, fakes);
    rerender({ filter: BASE, location: MANGWON, ready: true });
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(lastQuery(fakes)).toEqual({
      location: MANGWON,
      radiusKm: 3,
      sort: 'sales_end',
      keyword: '',
      page: 1,
      size: 20,
    });
    expect(result.current.items).toHaveLength(2);
  });

  it("위치 없음 + sort 'distance'면 요청은 sort 'sales_end'", async () => {
    const { fakes } = setup({
      filter: { ...BASE, sort: 'distance' },
      location: null,
      ready: true,
    });
    await waitFor(() => expect(fakes.offers.findNearby).toHaveBeenCalled());
    expect(lastQuery(fakes)).toMatchObject({ location: null, sort: 'sales_end' });
  });

  it('0건이면 empty', async () => {
    const { result } = setup({ filter: BASE, location: null, ready: true });
    await waitFor(() => expect(result.current.status).toBe('empty'));
    expect(result.current.items).toEqual([]);
    expect(result.current.hasMore).toBe(false);
  });

  it('실패하면 error, retry()는 1페이지를 다시 요청한다', async () => {
    const fakes = anonymousFakes();
    fakes.offers.findNearby.mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', 'x'));
    fakes.offers.findNearby.mockResolvedValueOnce(makeOfferPage(makeNearbyList(1)));
    const { result } = setup({ filter: BASE, location: null, ready: true }, fakes);
    await waitFor(() => expect(result.current.status).toBe('error'));
    act(() => result.current.retry());
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(fakes.offers.findNearby).toHaveBeenCalledTimes(2);
    expect(lastQuery(fakes)).toMatchObject({ page: 1 });
  });

  it('total 25에 20개면 hasMore, loadMore()는 page 2를 받아 이어 붙인다', async () => {
    const fakes = anonymousFakes();
    fakes.offers.findNearby.mockResolvedValueOnce(makeOfferPage(makeNearbyList(20), { total: 25 }));
    fakes.offers.findNearby.mockResolvedValueOnce(
      makeOfferPage(makeNearbyList(5, 21), { page: 2, total: 25 }),
    );
    const { result } = setup({ filter: BASE, location: null, ready: true }, fakes);
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current.hasMore).toBe(true);
    act(() => result.current.loadMore());
    await waitFor(() => expect(result.current.items).toHaveLength(25));
    expect(lastQuery(fakes)).toMatchObject({ page: 2 });
    expect(result.current.items[20]?.offer.id).toBe('o21');
    expect(result.current.hasMore).toBe(false);
  });

  it('필터가 바뀌면 앞 요청을 abort하고 목록을 초기화한 뒤 새로 받는다', async () => {
    const fakes = anonymousFakes();
    const first = deferred<OfferPage>();
    fakes.offers.findNearby.mockReturnValueOnce(first.promise);
    fakes.offers.findNearby.mockResolvedValueOnce(makeOfferPage(makeNearbyList(1, 9)));
    const { result, rerender } = setup({ filter: BASE, location: null, ready: true }, fakes);
    await waitFor(() => expect(fakes.offers.findNearby).toHaveBeenCalledTimes(1));
    const firstSignal = fakes.offers.findNearby.mock.calls[0]?.[1];
    rerender({ filter: { ...BASE, sort: 'price' }, location: null, ready: true });
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(firstSignal?.aborted).toBe(true);
    expect(lastQuery(fakes)).toMatchObject({ sort: 'price', page: 1 });
    expect(result.current.items.map((i) => i.offer.id)).toEqual(['o9']);
  });

  it('2페이지까지 본 뒤 같은 좌표로 위치를 다시 받으면 loading을 거쳐 1페이지만 남고, 다음 loadMore는 page 2', async () => {
    const fakes = anonymousFakes();
    const reloaded = deferred<OfferPage>();
    fakes.offers.findNearby
      .mockResolvedValueOnce(makeOfferPage(makeNearbyList(20), { total: 45 }))
      .mockResolvedValueOnce(makeOfferPage(makeNearbyList(20, 21), { page: 2, total: 45 }))
      .mockReturnValueOnce(reloaded.promise)
      .mockResolvedValueOnce(makeOfferPage(makeNearbyList(20, 21), { page: 2, total: 45 }));
    const { result, rerender } = setup({ filter: BASE, location: MANGWON, ready: true }, fakes);
    await waitFor(() => expect(result.current.status).toBe('success'));
    act(() => result.current.loadMore());
    await waitFor(() => expect(result.current.items).toHaveLength(40));

    // 위치 재요청: ready false(pending) → 같은 좌표로 ready true
    rerender({ filter: BASE, location: null, ready: false });
    rerender({ filter: BASE, location: MANGWON, ready: true });
    expect(result.current.status).toBe('loading');
    expect(result.current.items).toEqual([]);
    expect(result.current.hasMore).toBe(false);

    reloaded.resolve(makeOfferPage(makeNearbyList(20), { total: 45 }));
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current.items).toHaveLength(20);
    expect(lastQuery(fakes)).toMatchObject({ location: MANGWON, page: 1 });
    act(() => result.current.loadMore());
    await waitFor(() => expect(result.current.items).toHaveLength(40));
    expect(lastQuery(fakes)).toMatchObject({ page: 2 });
  });
});
