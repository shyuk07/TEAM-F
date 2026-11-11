import { vi } from 'vitest';
import type { StoreReservationRepository } from '@/features/reservations';

export class FakeStoreReservationRepository implements StoreReservationRepository {
  findByStore = vi.fn<StoreReservationRepository['findByStore']>(() =>
    Promise.resolve({ items: [], page: 1, size: 20, total: 0 }),
  );
}
