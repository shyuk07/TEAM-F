import type { NearbyQuery } from '@/features/offers/domain/nearbyQuery';
import { HttpOfferRepository } from '@/features/offers/infrastructure/httpOfferRepository';

const { request } = vi.hoisted(() => ({ request: vi.fn() }));

vi.mock('@/shared/api/client', () => ({
  request,
  apiGet: (path: string, signal?: AbortSignal) => request(path, { signal }),
  apiPost: (path: string, body?: unknown, signal?: AbortSignal) =>
    request(path, { method: 'POST', body, signal }),
}));

type Options = { method?: string; body?: unknown; signal?: AbortSignal; auth?: boolean };

const offerDto = {
  id: 'o1',
  product_id: 'p1',
  store_id: 's1',
  store_name: '망원베이커리',
  product_name: '소금빵 세트',
  original_price: 12000,
  sale_price: 6000,
  discount_rate: 50,
  initial_stock: 10,
  remaining_stock: 3,
  is_sold_out: false,
  sales_start: '2026-11-10T06:00:00Z',
  sales_end: '2026-11-10T09:00:00Z',
  pickup_start: '2026-11-10T09:00:00Z',
  pickup_end: '2026-11-10T11:00:00Z',
  status: 'ON_SALE',
  is_active: true,
};

function listDto(over: Record<string, unknown> = {}, distance: number | null = 0.42) {
  return {
    items: [{ offer: { ...offerDto, ...over }, distance, unit: 'km' }],
    page: 1,
    size: 20,
    total: 1,
  };
}

const query = (over: Partial<NearbyQuery> = {}): NearbyQuery => ({
  location: { lat: 37.5, lng: 126.9 },
  radiusKm: 3,
  sort: 'sales_end',
  keyword: '',
  page: 1,
  size: 20,
  ...over,
});

function lastCall(): { path: string; params: URLSearchParams; opts: Options } {
  const call = request.mock.calls.at(-1) ?? [];
  const path = String(call[0]);
  const [pathname, search = ''] = path.split('?');
  return {
    path: pathname ?? '',
    params: new URLSearchParams(search),
    opts: (call[1] ?? {}) as Options,
  };
}

describe('HttpOfferRepository.findNearby', () => {
  const repo = new HttpOfferRepository();

  beforeEach(() => {
    request.mockReset();
    request.mockResolvedValue(listDto());
  });

  it('위치가 있으면 lat·lng·radius_km·sort·page·size를 보내고 auth:false, signal 전달', async () => {
    const signal = new AbortController().signal;
    await repo.findNearby(query(), signal);
    const { path, params, opts } = lastCall();
    expect(path).toBe('/v1/offers');
    expect(Object.fromEntries(params)).toEqual({
      lat: '37.5',
      lng: '126.9',
      radius_km: '3',
      sort: 'sales_end',
      page: '1',
      size: '20',
    });
    expect(opts.auth).toBe(false);
    expect(opts.signal).toBe(signal);
    expect(opts.method ?? 'GET').toBe('GET');
  });

  it('위치가 없으면 lat·lng·radius_km를 빼고, 공백뿐인 keyword도 뺀다(status도 보내지 않음)', async () => {
    await repo.findNearby(query({ location: null, keyword: '   ' }));
    const { params } = lastCall();
    expect(params.has('lat')).toBe(false);
    expect(params.has('lng')).toBe(false);
    expect(params.has('radius_km')).toBe(false);
    expect(params.has('keyword')).toBe(false);
    expect(params.has('status')).toBe(false);
    await repo.findNearby(query({ keyword: '빵' }));
    expect(lastCall().params.get('keyword')).toBe('빵');
  });

  it('DTO를 Offer로 바꾼다(snake → camel, 날짜 Date, distance → distanceKm)', async () => {
    const page = await repo.findNearby(query());
    expect(page).toMatchObject({ page: 1, size: 20, total: 1 });
    const item = page.items[0];
    expect(item?.distanceKm).toBe(0.42);
    expect(item?.offer).toMatchObject({
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
      status: 'ON_SALE',
      isActive: true,
    });
    expect(item?.offer.salesEnd).toBeInstanceOf(Date);
    expect(item?.offer.salesEnd.getTime()).toBe(Date.parse('2026-11-10T09:00:00Z'));
    expect(item?.offer.pickupStart.getTime()).toBe(Date.parse('2026-11-10T09:00:00Z'));
  });

  it("status가 5개 밖('WEIRD')이면 reject", async () => {
    request.mockResolvedValue(listDto({ status: 'WEIRD' }));
    await expect(repo.findNearby(query())).rejects.toThrow();
  });
});
