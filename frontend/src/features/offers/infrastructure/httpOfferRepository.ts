import { request } from '@/shared/api/client';
import { API_BASE_URL } from '@/shared/config/env';
import type { NearbyQuery } from '../domain/nearbyQuery';
import type { NearbyOffer, Offer, OfferList, OfferPage, OfferStatus } from '../domain/offer';
import type { OfferDetail } from '../domain/offerDetail';
import type { OfferRepository } from '../domain/offerRepository';
import { type OfferDto, toOffer } from './offerDto';

type NearbyOfferListDto = {
  items: { offer: OfferDto; distance: number | null; unit: string }[];
  page: number;
  size: number;
  total: number;
};

type StoreOfferListDto = {
  items: OfferDto[];
  page: number;
  size: number;
  total: number;
};

// 백엔드 catalog/presentation/schemas.py OfferDetailResponse.
type OfferDetailDto = {
  offer: OfferDto;
  description: string | null;
  product_image: string[];
  pickup_address: string;
  latitude: number | null;
  longitude: number | null;
  notice: string;
  cancel_policy: { cancellable_until: string; description: string };
};

// 업로드 이미지 경로(/v1/products/{id}/images/{image_id}, catalog §17)는 서버 주소를 붙이고(offers.md D-3),
// https: 절대 URL만 그대로 쓴다. 그 밖(http:, data:, javascript:, //host, 상대 경로, 파싱 불가)은 버린다(F17).
function toImageUrl(s: string): string | null {
  if (s.startsWith('/') && !s.startsWith('//')) return `${API_BASE_URL}${s}`;
  try {
    return new URL(s).protocol === 'https:' ? s : null;
  } catch {
    return null;
  }
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

  // 공개 API라 토큰 없이 부른다(offers.md §3.1, D-4). 404·400 구분은 훅이 한다.
  async findById(id: string, signal?: AbortSignal): Promise<OfferDetail> {
    const dto = await request<OfferDetailDto>(`/v1/offers/${encodeURIComponent(id)}`, {
      auth: false,
      signal,
    });
    return {
      offer: toOffer(dto.offer),
      description: dto.description,
      imageUrls: dto.product_image.flatMap((s) => toImageUrl(s) ?? []),
      pickupAddress: dto.pickup_address,
      latitude: dto.latitude,
      longitude: dto.longitude,
      notice: dto.notice,
      cancellableUntil: new Date(dto.cancel_policy.cancellable_until),
      cancelPolicyText: dto.cancel_policy.description,
    };
  }

  async findByStore(
    storeId: string,
    statuses: OfferStatus[],
    page: number,
    size: number,
    signal?: AbortSignal,
  ): Promise<OfferList> {
    const params = new URLSearchParams();
    for (const s of statuses) {
      params.append('status', s);
    }
    params.set('page', String(page));
    params.set('size', String(size));

    const dto = await request<StoreOfferListDto>(
      `/v1/stores/${encodeURIComponent(storeId)}/offers?${params.toString()}`,
      { signal },
    );
    return {
      items: dto.items.map(toOffer),
      page: dto.page,
      size: dto.size,
      total: dto.total,
    };
  }

  async findOfferById(id: string, signal?: AbortSignal): Promise<Offer> {
    const dto = await request<OfferDetailDto>(`/v1/offers/${encodeURIComponent(id)}`, {
      signal,
    });
    return toOffer(dto.offer);
  }
}
