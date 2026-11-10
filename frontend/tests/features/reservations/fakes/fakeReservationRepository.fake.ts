import { vi } from 'vitest';
import type { ReservationRepository } from '@/features/reservations/domain/ports';
import { makeReservation } from './reservations';

export class FakeReservationRepository implements ReservationRepository {
  create = vi.fn<ReservationRepository['create']>(() =>
    Promise.resolve({
      id: 'r-new',
      offerId: 'o1',
      quantity: 1,
      unitPrice: 6000,
      totalPrice: 6000,
      status: 'PENDING_PAYMENT',
      createdAt: new Date('2026-11-10T15:00:00+09:00'),
      storeName: '망원베이커리',
      productName: '식빵 모둠',
    }),
  );
  listMine = vi.fn<ReservationRepository['listMine']>(() =>
    Promise.resolve({ items: [], page: 1, size: 100, total: 0 }),
  );
  get = vi.fn<ReservationRepository['get']>(() => Promise.resolve(makeReservation()));
  cancel = vi.fn<ReservationRepository['cancel']>((id: string) =>
    Promise.resolve({ id, status: 'CANCELLED', cancelledBy: 'CUSTOMER' }),
  );
}
