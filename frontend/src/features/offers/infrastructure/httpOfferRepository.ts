import { apiGet } from '@/shared/api/client';
import type { NearbyOffer, NearbyOfferPage, Offer, OfferStatus } from '../domain/offer';
import type { OfferRepository } from '../domain/offerRepository';
import type { NearbyOfferQuery } from '../domain/search';

type OfferDto = {
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

type NearbyOfferItemDto = { offer: OfferDto; distance: number | null; unit: string };

type NearbyOfferListDto = {
  items: NearbyOfferItemDto[];
  page: number;
  size: number;
  total: number;
};

const STATUSES: readonly OfferStatus[] = [
  'SCHEDULED',
  'ON_SALE',
  'SOLD_OUT',
  'CLOSED',
  'SUSPENDED',
];

function toStatus(value: string): OfferStatus {
  const hit = STATUSES.find((s) => s === value);
  if (hit === undefined) throw new Error(`알 수 없는 할인 상태: ${value}`);
  return hit;
}

function toOffer(d: OfferDto): Offer {
  return {
    id: d.id,
    productId: d.product_id,
    storeId: d.store_id,
    storeName: d.store_name,
    productName: d.product_name,
    originalPrice: d.original_price,
    salePrice: d.sale_price,
    discountRate: d.discount_rate,
    initialStock: d.initial_stock,
    remainingStock: d.remaining_stock,
    isSoldOut: d.is_sold_out,
    salesStart: new Date(d.sales_start),
    salesEnd: new Date(d.sales_end),
    pickupStart: new Date(d.pickup_start),
    pickupEnd: new Date(d.pickup_end),
    status: toStatus(d.status),
    isActive: d.is_active,
  };
}

function toNearbyOffer(d: NearbyOfferItemDto): NearbyOffer {
  return { offer: toOffer(d.offer), distanceKm: d.distance };
}

export class HttpOfferRepository implements OfferRepository {
  async findNearby(q: NearbyOfferQuery, signal?: AbortSignal): Promise<NearbyOfferPage> {
    const params = new URLSearchParams();
    if (q.area !== null) {
      params.set('lat', String(q.area.point.lat));
      params.set('lng', String(q.area.point.lng));
      params.set('radius_km', String(q.area.radiusKm));
    }
    if (q.keyword !== undefined) params.set('keyword', q.keyword);
    params.set('sort', q.sort);
    params.set('page', String(q.page));
    params.set('size', String(q.size));
    const dto = await apiGet<NearbyOfferListDto>(`/v1/offers?${params.toString()}`, signal);
    return {
      items: dto.items.map(toNearbyOffer),
      page: dto.page,
      size: dto.size,
      total: dto.total,
    };
  }
}
