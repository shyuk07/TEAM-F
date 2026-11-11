import { vi } from 'vitest';
import type { OfferRepository } from '@/features/offers';

// 기본: 빈 페이지
export class FakeOfferRepository implements OfferRepository {
  findNearby = vi.fn<OfferRepository['findNearby']>((query) =>
    Promise.resolve({ items: [], page: query.page, size: query.size, total: 0 }),
  );
}
