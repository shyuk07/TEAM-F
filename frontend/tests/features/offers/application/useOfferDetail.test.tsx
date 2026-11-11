import { act, waitFor } from '@testing-library/react';
import { useOfferDetail, type OfferDetail } from '@/features/offers';
import { ApiError } from '@/shared/api/error';
import { anonymousFakes, type AuthFakes } from '../../../support/authFakes';
import { deferred } from '../../auth/fakes/deferred';
import { makeOfferDetail } from '../fakes/offerDetails';
import { renderOffersHook } from './renderOffersHook';

type Props = { id: string };

function setup(fakes: AuthFakes, id = 'o1') {
  return renderOffersHook((p: Props) => useOfferDetail(p.id), { fakes, initialProps: { id } });
}

describe('useOfferDetail', () => {
  it('마운트하면 loading, 받으면 success + detail', async () => {
    const fakes = anonymousFakes();
    const pending = deferred<OfferDetail>();
    fakes.offers.findById.mockReturnValueOnce(pending.promise);
    const { result } = setup(fakes);
    expect(result.current.status).toBe('loading');
    expect(result.current.detail).toBeNull();
    expect(fakes.offers.findById.mock.calls[0]?.[0]).toBe('o1');
    const detail = makeOfferDetail();
    await act(async () => pending.resolve(detail));
    expect(result.current.status).toBe('success');
    expect(result.current.detail).toEqual(detail);
  });

  it.each([
    [404, 'OFFER_NOT_FOUND'],
    [400, 'VALIDATION_ERROR'],
  ])('%d → notFound', async (status, code) => {
    const fakes = anonymousFakes();
    fakes.offers.findById.mockRejectedValueOnce(new ApiError(status, code, ''));
    const { result } = setup(fakes);
    await waitFor(() => expect(result.current.status).toBe('notFound'));
    expect(result.current.detail).toBeNull();
  });

  it.each<[string, unknown]>([
    ['500', new ApiError(500, 'INTERNAL_ERROR', '')],
    ['네트워크', new TypeError('Failed to fetch')],
  ])('%s → error, retry() → loading → success', async (_name, err) => {
    const fakes = anonymousFakes();
    const again = deferred<OfferDetail>();
    fakes.offers.findById.mockRejectedValueOnce(err).mockReturnValueOnce(again.promise);
    const { result } = setup(fakes);
    await waitFor(() => expect(result.current.status).toBe('error'));
    act(() => result.current.retry());
    expect(result.current.status).toBe('loading');
    await act(async () => again.resolve(makeOfferDetail()));
    expect(result.current.status).toBe('success');
    expect(fakes.offers.findById).toHaveBeenCalledTimes(2);
  });

  it('언마운트하면 signal을 abort하고, 그 뒤 응답이 와도 상태를 바꾸지 않는다', async () => {
    const fakes = anonymousFakes();
    const pending = deferred<OfferDetail>();
    fakes.offers.findById.mockReturnValueOnce(pending.promise);
    const { result, unmount } = setup(fakes);
    const signal = fakes.offers.findById.mock.calls[0]?.[1];
    expect(signal).toBeInstanceOf(AbortSignal);
    unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => pending.resolve(makeOfferDetail()));
    expect(result.current.status).toBe('loading');
  });

  it('offerId가 바뀌면 앞 요청을 abort하고 새 id로 다시 요청한다', async () => {
    const fakes = anonymousFakes();
    const first = deferred<OfferDetail>();
    fakes.offers.findById
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce(makeOfferDetail({}, { id: 'o2' }));
    const { result, rerender } = setup(fakes);
    const firstSignal = fakes.offers.findById.mock.calls[0]?.[1];
    rerender({ id: 'o2' });
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(firstSignal?.aborted).toBe(true);
    expect(fakes.offers.findById.mock.calls.at(-1)?.[0]).toBe('o2');
    expect(result.current.detail?.offer.id).toBe('o2');
    await act(async () => first.resolve(makeOfferDetail({}, { id: 'o1' })));
    expect(result.current.detail?.offer.id).toBe('o2');
  });
});
