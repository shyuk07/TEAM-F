import { HttpOfferRepository } from '@/features/offers/infrastructure/httpOfferRepository';
import type { NearbyOfferQuery } from '@/features/offers';
import { ApiError } from '@/shared/api/error';

const { request } = vi.hoisted(() => ({ request: vi.fn() }));

vi.mock('@/shared/api/client', () => ({
  request,
  apiGet: (path: string, signal?: AbortSignal) => request(path, { signal }),
}));

function lastCall(): { path: string; opts: { signal?: AbortSignal } } {
  const call = request.mock.calls.at(-1) ?? [];
  return { path: call[0] as string, opts: (call[1] ?? {}) as { signal?: AbortSignal } };
}

const AREA = { point: { lat: 37.5, lng: 126.9 }, radiusKm: 3 };

const baseQuery: NearbyOfferQuery = {
  area: AREA,
  keyword: undefined,
  sort: 'sales_end',
  page: 1,
  size: 20,
};

function offerDto(overrides: Record<string, unknown> = {}) {
  return {
    id: '11111111-1111-4111-8111-111111111111',
    product_id: '22222222-2222-4222-8222-222222222222',
    store_id: '33333333-3333-4333-8333-333333333333',
    store_name: '망원베이커리',
    product_name: '식빵 모둠 5종',
    original_price: 12000,
    sale_price: 6000,
    discount_rate: 50,
    initial_stock: 10,
    remaining_stock: 3,
    is_sold_out: false,
    sales_start: '2026-11-10T06:00:00Z',
    sales_end: '2026-11-10T09:00:00+00:00',
    pickup_start: '2026-11-10T09:00:00Z',
    pickup_end: '2026-11-10T11:00:00Z',
    status: 'ON_SALE',
    is_active: true,
    ...overrides,
  };
}

function pageDto(items: unknown[]) {
  return { items, page: 1, size: 20, total: items.length };
}

describe('HttpOfferRepository.findNearby 요청', () => {
  const repo = new HttpOfferRepository();

  beforeEach(() => {
    request.mockReset();
    request.mockResolvedValue(pageDto([]));
  });

  it('위치·검색어가 있으면 정해진 순서로 쿼리를 만든다(한글은 인코딩)', async () => {
    await repo.findNearby({ ...baseQuery, keyword: '빵' });
    expect(lastCall().path).toBe(
      '/v1/offers?lat=37.5&lng=126.9&radius_km=3&keyword=%EB%B9%B5&sort=sales_end&page=1&size=20',
    );
  });

  it('위치가 없으면 lat·lng·radius_km을 보내지 않는다', async () => {
    await repo.findNearby({ ...baseQuery, area: null });
    expect(lastCall().path).toBe('/v1/offers?sort=sales_end&page=1&size=20');
  });

  it('검색어가 undefined면 keyword를 보내지 않는다', async () => {
    await repo.findNearby(baseQuery);
    expect(lastCall().path).not.toContain('keyword');
  });

  it('status·category는 보내지 않는다', async () => {
    await repo.findNearby({ ...baseQuery, keyword: '빵' });
    expect(lastCall().path).not.toContain('status');
    expect(lastCall().path).not.toContain('category');
  });

  it('signal을 그대로 넘긴다', async () => {
    const ctrl = new AbortController();
    await repo.findNearby(baseQuery, ctrl.signal);
    expect(lastCall().opts.signal).toBe(ctrl.signal);
  });
});

describe('HttpOfferRepository.findNearby 응답 변환', () => {
  const repo = new HttpOfferRepository();

  beforeEach(() => {
    request.mockReset();
  });

  it('snake_case 필드를 Offer(camelCase)로 바꾼다', async () => {
    request.mockResolvedValue(pageDto([{ offer: offerDto(), distance: 0.35, unit: 'km' }]));
    const page = await repo.findNearby(baseQuery);
    expect(page.page).toBe(1);
    expect(page.size).toBe(20);
    expect(page.total).toBe(1);
    const { offer, distanceKm } = page.items[0];
    expect(distanceKm).toBe(0.35);
    expect(offer).toMatchObject({
      id: '11111111-1111-4111-8111-111111111111',
      productId: '22222222-2222-4222-8222-222222222222',
      storeId: '33333333-3333-4333-8333-333333333333',
      storeName: '망원베이커리',
      productName: '식빵 모둠 5종',
      originalPrice: 12000,
      salePrice: 6000,
      discountRate: 50,
      initialStock: 10,
      remainingStock: 3,
      isSoldOut: false,
      status: 'ON_SALE',
      isActive: true,
    });
  });

  it('날짜 문자열을 Date로 바꾼다', async () => {
    request.mockResolvedValue(pageDto([{ offer: offerDto(), distance: null, unit: 'km' }]));
    const { offer } = (await repo.findNearby(baseQuery)).items[0];
    expect(offer.salesStart).toBeInstanceOf(Date);
    expect(offer.salesStart.getTime()).toBe(new Date('2026-11-10T06:00:00Z').getTime());
    expect(offer.salesEnd.getTime()).toBe(new Date('2026-11-10T09:00:00+00:00').getTime());
    expect(offer.pickupStart.getTime()).toBe(new Date('2026-11-10T09:00:00Z').getTime());
    expect(offer.pickupEnd.getTime()).toBe(new Date('2026-11-10T11:00:00Z').getTime());
  });

  it('distance가 null이면 distanceKm도 null', async () => {
    request.mockResolvedValue(pageDto([{ offer: offerDto(), distance: null, unit: 'km' }]));
    expect((await repo.findNearby(baseQuery)).items[0].distanceKm).toBeNull();
  });

  it('discount_rate는 계산하지 않고 서버 값을 그대로 쓴다', async () => {
    // 6000/12000이면 50%지만 서버가 33이라고 하면 33이다
    request.mockResolvedValue(
      pageDto([{ offer: offerDto({ discount_rate: 33 }), distance: null, unit: 'km' }]),
    );
    expect((await repo.findNearby(baseQuery)).items[0].offer.discountRate).toBe(33);
  });

  it('알 수 없는 status면 Error를 던진다(알려진 status는 변환된다)', async () => {
    request.mockResolvedValue(pageDto([{ offer: offerDto(), distance: null, unit: 'km' }]));
    await expect(repo.findNearby(baseQuery)).resolves.toMatchObject({ total: 1 });
    request.mockResolvedValue(
      pageDto([{ offer: offerDto({ status: 'WHATEVER' }), distance: null, unit: 'km' }]),
    );
    await expect(repo.findNearby(baseQuery)).rejects.toBeInstanceOf(Error);
  });

  it('ApiError는 그대로 전파한다', async () => {
    const err = new ApiError(500, 'INTERNAL_ERROR', '서버 오류');
    request.mockRejectedValue(err);
    await expect(repo.findNearby(baseQuery)).rejects.toBe(err);
  });
});
