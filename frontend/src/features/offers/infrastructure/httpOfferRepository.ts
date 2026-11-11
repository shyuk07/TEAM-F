import { request } from '@/shared/api/client';
import type { NearbyQuery } from '../domain/nearbyQuery';
import type { NearbyOffer, Offer, OfferPage, OfferStatus } from '../domain/offer';
import type { OfferRepository } from '../domain/offerRepository';

// DTO 타입은 이 파일 안에서만 쓴다(F9). 백엔드 catalog/presentation/schemas.py OfferResponse·NearbyOfferItem.
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

type NearbyOfferListDto = {
  items: { offer: OfferDto; distance: number | null; unit: string }[];
  page: number;
  size: number;
  total: number;
};

const OFFER_STATUSES: readonly OfferStatus[] = [
  'SCHEDULED',
  'ON_SALE',
  'SOLD_OUT',
  'CLOSED',
  'SUSPENDED',
];

function toStatus(value: string): OfferStatus {
  const hit = OFFER_STATUSES.find((s) => s === value);
  if (hit === undefined) throw new Error(`알 수 없는 할인 상태: ${value}`);
  return hit;
}

function toOffer(dto: OfferDto): Offer {
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

// TODO: 기본 상태(ON_SALE)만 받아 품절 카드가 거의 나오지 않는다.
//   왜: status는 한 값만 받는다. 판매 중 + 품절을 함께 보여 줄지 정해지지 않았다 (docs/design/frontend/customer-home.md C-3)
//   언제: 결정 후 (사용자: 홈 목록에 품절 포함 여부)
export class HttpOfferRepository implements OfferRepository {
  async findNearby(query: NearbyQuery, signal?: AbortSignal): Promise<OfferPage> {
    const params = new URLSearchParams();
    if (query.location !== null) {
      params.set('lat', String(query.location.lat));
      params.set('lng', String(query.location.lng));
      params.set('radius_km', String(query.radiusKm));
    }
    const keyword = query.keyword.trim();
    if (keyword !== '') params.set('keyword', keyword);
    params.set('sort', query.sort);
    params.set('page', String(query.page));
    params.set('size', String(query.size));
    // 공개 API라 토큰을 붙이지 않는다. 남은 만료 토큰이 목록 요청을 막지 않게 한다(customer-home.md D-19).
    const dto = await request<NearbyOfferListDto>(`/v1/offers?${params.toString()}`, {
      auth: false,
      signal,
    });
    const items: NearbyOffer[] = dto.items.map((item) => ({
      offer: toOffer(item.offer),
      distanceKm: item.distance,
    }));
    return { items, page: dto.page, size: dto.size, total: dto.total };
  }
}
