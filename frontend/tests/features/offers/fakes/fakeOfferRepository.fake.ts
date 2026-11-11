import { vi } from 'vitest';
import type { OfferRepository } from '@/features/offers';
import { ApiError } from '@/shared/api/error';

// 기본: 빈 페이지, 상세는 404(없는 할인)
export class FakeOfferRepository implements OfferRepository {
  findNearby = vi.fn<OfferRepository['findNearby']>((query) =>
    Promise.resolve({ items: [], page: query.page, size: query.size, total: 0 }),
  );
  findById = vi.fn<OfferRepository['findById']>(() =>
    Promise.reject(new ApiError(404, 'OFFER_NOT_FOUND', '할인을 찾을 수 없습니다.')),
  );
  findByStore = vi.fn<OfferRepository['findByStore']>((_storeId, _statuses, page, size) =>
    Promise.resolve({ items: [], page, size, total: 0 }),
  );
  findOfferById = vi.fn<OfferRepository['findOfferById']>(() =>
    Promise.reject(new ApiError(404, 'OFFER_NOT_FOUND', '할인을 찾을 수 없습니다.')),
  );
}
