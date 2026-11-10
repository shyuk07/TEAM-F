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

export type NearbyOffer = { offer: Offer; distanceKm: number | null };

export type OfferPage = { items: NearbyOffer[]; page: number; size: number; total: number };

export function isSoldOut(offer: Offer): boolean {
  void offer;
  throw new Error('not implemented: isSoldOut');
}
