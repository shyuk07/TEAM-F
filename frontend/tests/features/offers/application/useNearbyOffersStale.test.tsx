import { waitFor } from '@testing-library/react';
import {
  useNearbyOffers,
  type NearbyOffersView,
} from '@/features/offers/application/useNearbyOffers';
import type { NearbyOfferQuery } from '@/features/offers';
import { manyOffers, pageOf } from '../fakes/offers';
import { defaultOfferFakes, renderOffersHook } from '../../../support/renderWithOffers';

const query: NearbyOfferQuery = {
  area: null,
  keyword: undefined,
  sort: 'sales_end',
  page: 1,
  size: 20,
};

describe('useNearbyOffers: 질의가 바뀐 직후', () => {
  it('effect가 돌기 전 렌더에서도 이전 질의의 목록을 내놓지 않는다', async () => {
    const offerFakes = defaultOfferFakes();
    offerFakes.offers.findNearby.mockResolvedValue(pageOf(manyOffers(20, 'a'), 1, 20, 45));
    const seen: NearbyOffersView[] = [];
    const { result, rerender } = renderOffersHook(
      ({ q }: { q: NearbyOfferQuery }) => {
        const view = useNearbyOffers(q);
        seen.push(view);
        return view;
      },
      { offerFakes, initialProps: { q: query } },
    );
    await waitFor(() => expect(result.current.status).toBe('success'));
    const before = seen.length;
    rerender({ q: { ...query, sort: 'price' } });
    const first = seen[before];
    expect(first.status).toBe('loading');
    expect(first.items).toEqual([]);
    expect(first.hasMore).toBe(false);
  });
});
