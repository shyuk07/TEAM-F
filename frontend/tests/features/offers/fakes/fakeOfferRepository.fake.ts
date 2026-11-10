import { vi } from 'vitest';
import type { OfferRepository } from '@/features/offers';
import { nearby, offerOnSale, pageOf } from './offers';

/** findNearby는 vi.fn이라 호출 인자(조회 조건·signal)가 기록된다. 기본값: 판매 중 카드 1장(0.4km). */
export class FakeOfferRepository implements OfferRepository {
  findNearby = vi
    .fn<OfferRepository['findNearby']>()
    .mockResolvedValue(pageOf([nearby(offerOnSale, 0.4)]));
}
