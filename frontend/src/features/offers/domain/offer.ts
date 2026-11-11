// TODO: 상품 정보(productId·productName·originalPrice)와 금액 표기가 entities/product의 Product·formatProductPrice와 겹친다.
//   왜: products가 entities/product를 만들었다 (docs/design/frontend/products.md D-7, §1.1)
//   언제: O3 구현 시
export type OfferStatus = 'SCHEDULED' | 'ON_SALE' | 'SOLD_OUT' | 'CLOSED' | 'SUSPENDED';

export type Offer = {
  id: string;
  productId: string;
  storeId: string;
  storeName: string;
  productName: string;
  originalPrice: number;
  salePrice: number;
  discountRate: number;
  initialStock: number;
  remainingStock: number;
  isSoldOut: boolean;
  salesStart: Date;
  salesEnd: Date;
  pickupStart: Date;
  pickupEnd: Date;
  status: OfferStatus;
  isActive: boolean;
};

export type NearbyOffer = { offer: Offer; distanceKm: number | null; imageUrls: string[] };

export type OfferPage = { items: NearbyOffer[]; page: number; size: number; total: number };

export type OfferList = { items: Offer[]; page: number; size: number; total: number };

export function isSoldOut(offer: Offer): boolean {
  return offer.isSoldOut || offer.status === 'SOLD_OUT' || offer.remainingStock <= 0;
}
