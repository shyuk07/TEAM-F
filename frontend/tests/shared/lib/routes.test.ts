import { describe, expect, it } from 'vitest';
import { ROUTES } from '@/shared/lib/routes';

describe('shared/lib routes', () => {
  it('ownerOfferNewFor는 productId를 인코딩해 쿼리에 붙인다', () => {
    expect(ROUTES.ownerOfferNewFor('a b')).toBe('/owner/offers/new?productId=a%20b');
  });

  it('ownerOfferNewFor는 평범한 id를 그대로 붙인다', () => {
    expect(ROUTES.ownerOfferNewFor('p1')).toBe('/owner/offers/new?productId=p1');
  });
});
