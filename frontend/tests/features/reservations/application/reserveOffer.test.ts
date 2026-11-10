import { reserveOffer } from '@/features/reservations/application/reserveOffer';
import { ApiError } from '@/shared/api/error';
import { FakeReservationRepository } from '../fakes/fakeReservationRepository.fake';
import { makeReservation } from '../fakes/reservations';

const input = { offerId: 'o1', quantity: 2 };

describe('reserveOffer', () => {
  it('201이면 created와 새 예약 id', async () => {
    const repo = new FakeReservationRepository();
    const result = await reserveOffer(repo, input, new AbortController().signal);
    expect(repo.create).toHaveBeenCalledWith(input, expect.anything());
    expect(result).toEqual({ kind: 'created', reservationId: 'r-new' });
  });

  it('409 PENDING_RESERVATION_EXISTS면 PENDING_PAYMENT 목록에서 같은 할인의 예약 id를 찾는다', async () => {
    const repo = new FakeReservationRepository();
    repo.create.mockRejectedValue(new ApiError(409, 'PENDING_RESERVATION_EXISTS', '중복'));
    repo.listMine.mockResolvedValue({
      items: [
        makeReservation({ id: 'other', offerId: 'o2', status: 'PENDING_PAYMENT' }),
        makeReservation({ id: 'found', offerId: 'o1', status: 'PENDING_PAYMENT' }),
      ],
      page: 1,
      size: 100,
      total: 2,
    });
    const result = await reserveOffer(repo, input, new AbortController().signal);
    expect(repo.listMine.mock.calls[0]?.[0]).toMatchObject({ status: 'PENDING_PAYMENT' });
    expect(result).toEqual({ kind: 'pendingExists', reservationId: 'found' });
  });

  it('409 PENDING_RESERVATION_EXISTS인데 찾지 못하면 id null', async () => {
    const repo = new FakeReservationRepository();
    repo.create.mockRejectedValue(new ApiError(409, 'PENDING_RESERVATION_EXISTS', '중복'));
    const result = await reserveOffer(repo, input, new AbortController().signal);
    expect(result).toEqual({ kind: 'pendingExists', reservationId: null });
  });

  it('409 OUT_OF_STOCK은 그대로 throw', async () => {
    const repo = new FakeReservationRepository();
    const err = new ApiError(409, 'OUT_OF_STOCK', '재고 부족');
    repo.create.mockRejectedValue(err);
    await expect(reserveOffer(repo, input, new AbortController().signal)).rejects.toBe(err);
    expect(repo.listMine).not.toHaveBeenCalled();
  });
});
