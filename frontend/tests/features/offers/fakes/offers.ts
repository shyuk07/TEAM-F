import type { NearbyOffer, NearbyOfferPage, Offer } from '@/features/offers';

/** 시간 고정값(로컬 시간 생성자: 시간대에 의존하지 않는다). offers.md §7 */
export const now = new Date(2026, 10, 10, 17, 18, 0);

export const minutesFromNow = (m: number) => new Date(now.getTime() + m * 60_000);

export function makeOffer(overrides: Partial<Offer> = {}): Offer {
  return {
    id: 'offer-1',
    productId: 'product-1',
    storeId: 'store-1',
    storeName: '망원베이커리',
    productName: '식빵 모둠 5종',
    originalPrice: 12000,
    salePrice: 6000,
    discountRate: 50,
    initialStock: 10,
    remainingStock: 3,
    isSoldOut: false,
    salesStart: minutesFromNow(-120),
    salesEnd: minutesFromNow(42),
    pickupStart: new Date(2026, 10, 10, 18, 0),
    pickupEnd: new Date(2026, 10, 10, 20, 0),
    status: 'ON_SALE',
    isActive: true,
    ...overrides,
  };
}

/** 판매 중: salesEnd = now+42분, 남은 3개, 할인율 50, 6000/12000 */
export const offerOnSale: Offer = makeOffer();

export const offerSoldOut: Offer = makeOffer({
  id: 'offer-2',
  productName: '단팥빵',
  remainingStock: 0,
  isSoldOut: true,
  status: 'SOLD_OUT',
});

export const offerEnded: Offer = makeOffer({
  id: 'offer-3',
  productName: '크루아상',
  status: 'CLOSED',
  salesEnd: minutesFromNow(-10),
});

export const offerScheduled: Offer = makeOffer({
  id: 'offer-4',
  productName: '바게트',
  status: 'SCHEDULED',
  salesStart: minutesFromNow(30),
  salesEnd: minutesFromNow(120),
});

export function nearby(offer: Offer, distanceKm: number | null = 0.4): NearbyOffer {
  return { offer, distanceKm };
}

export function pageOf(
  items: NearbyOffer[],
  page = 1,
  size = 20,
  total = items.length,
): NearbyOfferPage {
  return { items, page, size, total };
}

/** id가 `${prefix}-${번호}`인 판매 중 항목 n개 */
export function manyOffers(n: number, prefix = 'p1', distanceKm: number | null = 0.4) {
  return Array.from({ length: n }, (_, i) =>
    nearby(
      makeOffer({ id: `${prefix}-${i + 1}`, productName: `${prefix} 상품 ${i + 1}` }),
      distanceKm,
    ),
  );
}
