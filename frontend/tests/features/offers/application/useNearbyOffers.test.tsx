import { act, waitFor } from '@testing-library/react';
import { useNearbyOffers } from '@/features/offers/application/useNearbyOffers';
import type { NearbyOfferPage, NearbyOfferQuery } from '@/features/offers';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../auth/fakes/deferred';
import { manyOffers, pageOf } from '../fakes/offers';
import {
  defaultOfferFakes,
  renderOffersHook,
  type OfferFakes,
} from '../../../support/renderWithOffers';

const query: NearbyOfferQuery = {
  area: { point: { lat: 37.5, lng: 126.9 }, radiusKm: 3 },
  keyword: undefined,
  sort: 'sales_end',
  page: 1,
  size: 20,
};

type Props = { q: NearbyOfferQuery | null };

/** configure로 가짜 저장소의 응답을 렌더 전에 정한다. */
function setup(
  q: NearbyOfferQuery | null = query,
  configure: (fakes: OfferFakes) => void = () => {},
) {
  const offerFakes = defaultOfferFakes();
  configure(offerFakes);
  return renderOffersHook(({ q: current }: Props) => useNearbyOffers(current), {
    offerFakes,
    initialProps: { q },
  });
}

const firstPage = () => pageOf(manyOffers(20, 'a'), 1, 20, 45);

/** 첫 쪽이 성공한 상태(hasMore true)로 시작한다. */
async function setupLoaded(configure: (fakes: OfferFakes) => void = () => {}) {
  const view = setup(query, (f) => {
    f.offers.findNearby.mockResolvedValueOnce(firstPage());
    configure(f);
  });
  await waitFor(() => expect(view.result.current.status).toBe('success'));
  return view;
}

describe('useNearbyOffers', () => {
  it('query가 null이면 loading이고 포트를 부르지 않는다', async () => {
    const { result, offerFakes } = setup(null);
    await act(async () => {});
    expect(result.current.status).toBe('loading');
    expect(offerFakes.offers.findNearby).not.toHaveBeenCalled();
  });

  it('성공: loading → success(items·total)', async () => {
    const { result } = setup();
    expect(result.current.status).toBe('loading');
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current.items).toHaveLength(1);
    expect(result.current.total).toBe(1);
  });

  it('결과 0건이면 empty', async () => {
    const { result } = setup(query, (f) => f.offers.findNearby.mockResolvedValue(pageOf([])));
    await waitFor(() => expect(result.current.status).toBe('empty'));
    expect(result.current.items).toEqual([]);
  });

  it('실패(ApiError 500)면 error', async () => {
    const { result } = setup(query, (f) =>
      f.offers.findNearby.mockRejectedValue(new ApiError(500, 'INTERNAL_ERROR', '서버')),
    );
    await waitFor(() => expect(result.current.status).toBe('error'));
  });

  it('reload() → 다시 loading → success', async () => {
    const { result, offerFakes } = await setupLoaded();
    const d = deferred<NearbyOfferPage>();
    offerFakes.offers.findNearby.mockReturnValueOnce(d.promise);
    act(() => result.current.reload());
    expect(result.current.status).toBe('loading');
    await act(async () => d.resolve(pageOf(manyOffers(2, 'r'))));
    expect(result.current.status).toBe('success');
    expect(result.current.items).toHaveLength(2);
    expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(2);
  });

  it('조건이 바뀌면 이전 signal을 abort하고 새 조건으로 1쪽을 요청한다', async () => {
    const pending = deferred<NearbyOfferPage>();
    const { rerender, offerFakes } = setup(query, (f) =>
      f.offers.findNearby.mockReturnValueOnce(pending.promise),
    );
    await waitFor(() => expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(1));
    const firstSignal = offerFakes.offers.findNearby.mock.calls[0][1];
    rerender({ q: { ...query, sort: 'price' } });
    await waitFor(() => expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(2));
    expect(firstSignal?.aborted).toBe(true);
    expect(offerFakes.offers.findNearby.mock.calls[1][0]).toMatchObject({ sort: 'price', page: 1 });
  });

  it('첫 요청 인자는 page 1, size 20', async () => {
    const { offerFakes } = setup();
    await waitFor(() => expect(offerFakes.offers.findNearby).toHaveBeenCalled());
    expect(offerFakes.offers.findNearby.mock.calls[0][0]).toMatchObject({ page: 1, size: 20 });
  });

  it('loadMore() → page 2 요청, loadingMore true → 이어 붙음', async () => {
    const { result, offerFakes } = await setupLoaded();
    expect(result.current.hasMore).toBe(true);
    const d = deferred<NearbyOfferPage>();
    offerFakes.offers.findNearby.mockReturnValueOnce(d.promise);
    act(() => result.current.loadMore());
    expect(result.current.loadingMore).toBe(true);
    expect(offerFakes.offers.findNearby.mock.calls.at(-1)?.[0]).toMatchObject({ page: 2 });
    await act(async () => d.resolve(pageOf(manyOffers(20, 'b'), 2, 20, 45)));
    expect(result.current.loadingMore).toBe(false);
    expect(result.current.items).toHaveLength(40);
  });

  it('마지막 쪽이면 hasMore false, loadMore()는 요청하지 않는다', async () => {
    const view = setup(query, (f) =>
      f.offers.findNearby.mockResolvedValue(pageOf(manyOffers(20, 'a'), 1, 20, 20)),
    );
    await waitFor(() => expect(view.result.current.status).toBe('success'));
    expect(view.result.current.hasMore).toBe(false);
    act(() => view.result.current.loadMore());
    expect(view.offerFakes.offers.findNearby).toHaveBeenCalledTimes(1);
  });

  it('loadMore() 실패 → 목록 유지·moreFailed → 다시 loadMore()로 성공', async () => {
    const { result, offerFakes } = await setupLoaded();
    offerFakes.offers.findNearby.mockRejectedValueOnce(new ApiError(500, 'INTERNAL_ERROR', 'x'));
    act(() => result.current.loadMore());
    await waitFor(() => expect(result.current.moreFailed).toBe(true));
    expect(result.current.status).toBe('success');
    expect(result.current.items).toHaveLength(20);
    expect(result.current.loadingMore).toBe(false);

    offerFakes.offers.findNearby.mockResolvedValueOnce(pageOf(manyOffers(20, 'b'), 2, 20, 45));
    act(() => result.current.loadMore());
    await waitFor(() => expect(result.current.items).toHaveLength(40));
    expect(result.current.moreFailed).toBe(false);
    expect(offerFakes.offers.findNearby.mock.calls.at(-1)?.[0]).toMatchObject({ page: 2 });
  });

  it('불러오는 중 loadMore()를 두 번 불러도 요청은 1회', async () => {
    const { result, offerFakes } = await setupLoaded();
    const before = offerFakes.offers.findNearby.mock.calls.length;
    offerFakes.offers.findNearby.mockReturnValue(deferred<NearbyOfferPage>().promise);
    act(() => {
      result.current.loadMore();
      result.current.loadMore();
    });
    expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(before + 1);
  });

  it('언마운트하면 signal을 abort하고 이후 상태를 바꾸지 않는다', async () => {
    const d = deferred<NearbyOfferPage>();
    const { result, unmount, offerFakes } = setup(query, (f) =>
      f.offers.findNearby.mockReturnValueOnce(d.promise),
    );
    await waitFor(() => expect(offerFakes.offers.findNearby).toHaveBeenCalledTimes(1));
    const signal = offerFakes.offers.findNearby.mock.calls[0][1];
    unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => d.resolve(pageOf(manyOffers(3, 'z'))));
    expect(result.current.status).toBe('loading');
  });
});
