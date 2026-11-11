import type { NearbyOffer, Offer, OfferPage } from '@/features/offers';
import { at } from '../../../support/clock';

// 기본값: 오늘(11/10) 18:00 판매 마감(고정 시각 17:18 기준 42분 전), 픽업 오늘 18:00–20:00, 남은 3개.
export function makeOffer(over: Partial<Offer> = {}): Offer {
  return {
    id: 'o1',
    productId: 'p1',
    storeId: 's1',
    storeName: '망원베이커리',
    productName: '소금빵 세트',
    originalPrice: 12000,
    salePrice: 6000,
    discountRate: 50,
    initialStock: 10,
    remainingStock: 3,
    isSoldOut: false,
    salesStart: at(10, 15, 0),
    salesEnd: at(10, 18, 0),
    pickupStart: at(10, 18, 0),
    pickupEnd: at(10, 20, 0),
    status: 'ON_SALE',
    isActive: true,
    ...over,
  };
}

export function makeNearby(
  over: Partial<Offer> = {},
  distanceKm: number | null = null,
  imageUrls: string[] = [],
): NearbyOffer {
  return { offer: makeOffer(over), distanceKm, imageUrls };
}

/** id가 o1…oN인 할인 N개. */
export function makeNearbyList(count: number, start = 1, distanceKm: number | null = null) {
  return Array.from({ length: count }, (_, i) =>
    makeNearby({ id: `o${start + i}`, productName: `상품 ${start + i}` }, distanceKm),
  );
}

export function makeOfferPage(
  items: NearbyOffer[],
  over: Partial<Omit<OfferPage, 'items'>> = {},
): OfferPage {
  return { items, page: 1, size: 20, total: items.length, ...over };
}
