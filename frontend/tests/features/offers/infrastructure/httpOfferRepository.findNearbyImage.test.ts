import type { NearbyQuery } from '@/features/offers/domain/nearbyQuery';
import { HttpOfferRepository } from '@/features/offers/infrastructure/httpOfferRepository';
import { API_BASE_URL } from '@/shared/config/env';

const { request } = vi.hoisted(() => ({ request: vi.fn() }));

vi.mock('@/shared/api/client', () => ({
  request,
  apiGet: (path: string, signal?: AbortSignal) => request(path, { signal }),
}));

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

function listDto(item: Record<string, unknown>) {
  return {
    items: [{ offer: offerDto, distance: 0.42, unit: 'km', ...item }],
    page: 1,
    size: 20,
    total: 1,
  };
}

const query: NearbyQuery = {
  location: { lat: 37.5, lng: 126.9 },
  radiusKm: 3,
  sort: 'sales_end',
  keyword: '',
  page: 1,
  size: 20,
};

describe('HttpOfferRepository.findNearby 상품 이미지(items[].product_image → imageUrls)', () => {
  const repo = new HttpOfferRepository();

  beforeEach(() => request.mockReset());

  it.each([
    [
      '업로드 이미지 경로는 API_BASE_URL을 붙인다',
      ['/v1/products/p/images/i'],
      [`${API_BASE_URL}/v1/products/p/images/i`],
    ],
    ['https 절대 URL은 그대로', ['https://x/a.jpg'], ['https://x/a.jpg']],
    ['http URL은 버린다', ['http://x/a.jpg'], []],
    ['data: URL은 버린다', ['data:image/png;base64,AAAA'], []],
    ['//host는 버린다', ['//evil.com/x'], []],
    ['빈 배열은 []', [], []],
    [
      '섞여 있으면 허용된 것만 순서대로',
      ['http://x/a.jpg', '/v1/products/p/images/i', '//evil.com/x', 'https://x/b.jpg'],
      [`${API_BASE_URL}/v1/products/p/images/i`, 'https://x/b.jpg'],
    ],
  ])('%s', async (_name, images, urls) => {
    request.mockResolvedValue(listDto({ product_image: images }));
    const page = await repo.findNearby(query);
    expect(page.items[0]?.imageUrls).toEqual(urls);
  });

  it('product_image 필드가 없으면 imageUrls는 []', async () => {
    request.mockResolvedValue(listDto({}));
    const page = await repo.findNearby(query);
    expect(page.items[0]?.imageUrls).toEqual([]);
    expect(page.items[0]?.distanceKm).toBe(0.42);
  });
});
