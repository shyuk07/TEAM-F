import { fetchAllMine } from '@/features/reservations/application/fetchAllMine';
import type { Reservation } from '@/features/reservations';
import { FakeReservationRepository } from '../fakes/fakeReservationRepository.fake';
import { makeReservation } from '../fakes/reservations';

function many(n: number, prefix: string): Reservation[] {
  return Array.from({ length: n }, (_, i) => makeReservation({ id: `${prefix}${i}` }));
}

describe('fetchAllMine', () => {
  it('total 150이면 size 100으로 page 1·2를 불러 150건을 합친다', async () => {
    const repo = new FakeReservationRepository();
    repo.listMine.mockImplementation((q) =>
      Promise.resolve({
        items: q.page === 1 ? many(100, 'a') : many(50, 'b'),
        page: q.page,
        size: 100,
        total: 150,
      }),
    );
    const result = await fetchAllMine(repo, new AbortController().signal);
    expect(repo.listMine).toHaveBeenCalledTimes(2);
    expect(repo.listMine.mock.calls[0]?.[0]).toMatchObject({ page: 1, size: 100 });
    expect(repo.listMine.mock.calls[1]?.[0]).toMatchObject({ page: 2, size: 100 });
    expect(result).toHaveLength(150);
  });

  it('total 0이면 한 번만 불러 빈 배열', async () => {
    const repo = new FakeReservationRepository();
    const result = await fetchAllMine(repo, new AbortController().signal);
    expect(repo.listMine).toHaveBeenCalledTimes(1);
    expect(result).toEqual([]);
  });

  it('status와 signal을 listMine에 넘긴다', async () => {
    const repo = new FakeReservationRepository();
    const ctrl = new AbortController();
    await fetchAllMine(repo, ctrl.signal, 'PENDING_PAYMENT');
    expect(repo.listMine.mock.calls[0]?.[0]).toMatchObject({ status: 'PENDING_PAYMENT' });
    expect(repo.listMine.mock.calls[0]?.[1]).toBe(ctrl.signal);
  });
});
