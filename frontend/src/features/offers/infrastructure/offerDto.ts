import type { Offer, OfferStatus } from '../domain/offer';

export type OfferDto = {
  id: string;
  product_id: string;
  store_id: string;
  store_name: string;
  product_name: string;
  original_price: number;
  sale_price: number;
  discount_rate: number;
  initial_stock: number;
  remaining_stock: number;
  is_sold_out: boolean;
  sales_start: string;
  sales_end: string;
  pickup_start: string;
  pickup_end: string;
  status: string;
  is_active: boolean;
};

export const OFFER_STATUSES: readonly OfferStatus[] = [
  'SCHEDULED',
  'ON_SALE',
  'SOLD_OUT',
  'CLOSED',
  'SUSPENDED',
];

export function toStatus(value: string): OfferStatus {
  const hit = OFFER_STATUSES.find((s) => s === value);
  if (hit === undefined) throw new Error(`알 수 없는 할인 상태: ${value}`);
  return hit;
}

export function toOffer(dto: OfferDto): Offer {
  return {
    id: String(dto.id),
    productId: String(dto.product_id),
    storeId: String(dto.store_id),
    storeName: dto.store_name,
    productName: dto.product_name,
    originalPrice: dto.original_price,
    salePrice: dto.sale_price,
    discountRate: dto.discount_rate,
    initialStock: dto.initial_stock,
    remainingStock: dto.remaining_stock,
    isSoldOut: dto.is_sold_out,
    salesStart: new Date(dto.sales_start),
    salesEnd: new Date(dto.sales_end),
    pickupStart: new Date(dto.pickup_start),
    pickupEnd: new Date(dto.pickup_end),
    status: toStatus(dto.status),
    isActive: dto.is_active,
  };
}
