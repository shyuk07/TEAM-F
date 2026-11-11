import { HttpOfferRepository } from '@/features/offers/infrastructure/httpOfferRepository';
import { ApiError } from '@/shared/api/error';
import { API_BASE_URL } from '@/shared/config/env';

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

function detailDto(over: Record<string, unknown> = {}) {
  return {
    offer: offerDto,
    description: null,
    product_image: [],
    pickup_address: '서울시 마포구 망원로 1',
    latitude: 37.556,
    longitude: 126.901,
    notice: '픽업 시 예약 확인 코드를 보여주세요.',
    cancel_policy: {
      cancellable_until: '2026-11-10T08:00:00Z',
      description: '취소 시 위약금이 발생할 수 있습니다.',
    },
    ...over,
  };
}

function lastCall(): { path: string; opts: Options } {
  const call = request.mock.calls.at(-1) ?? [];
  return { path: String(call[0]), opts: (call[1] ?? {}) as Options };
}

describe('HttpOfferRepository.findById', () => {
  const repo = new HttpOfferRepository();

  beforeEach(() => {
    request.mockReset();
    request.mockResolvedValue(detailDto());
  });

  it('GET /v1/offers/{id}를 토큰 없이(auth:false) 부르고 signal을 넘긴다', async () => {
    const signal = new AbortController().signal;
    await repo.findById('o1', signal);
    const { path, opts } = lastCall();
    expect(path).toBe('/v1/offers/o1');
    expect(opts.method ?? 'GET').toBe('GET');
    expect(opts.auth).toBe(false);
    expect(opts.signal).toBe(signal);
  });

  it('응답을 OfferDetail로 바꾼다(cancellableUntil Date, description null 유지, offer 17필드)', async () => {
    const detail = await repo.findById('o1');
    expect(detail).toEqual({
      offer: {
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
        salesStart: new Date('2026-11-10T06:00:00Z'),
        salesEnd: new Date('2026-11-10T09:00:00Z'),
        pickupStart: new Date('2026-11-10T09:00:00Z'),
        pickupEnd: new Date('2026-11-10T11:00:00Z'),
        status: 'ON_SALE',
        isActive: true,
      },
      description: null,
      imageUrls: [],
      pickupAddress: '서울시 마포구 망원로 1',
      latitude: 37.556,
      longitude: 126.901,
      notice: '픽업 시 예약 확인 코드를 보여주세요.',
      cancellableUntil: new Date('2026-11-10T08:00:00Z'),
      cancelPolicyText: '취소 시 위약금이 발생할 수 있습니다.',
    });
    expect(detail.cancellableUntil).toBeInstanceOf(Date);
  });

  it.each<[string, string[], string[]]>([
    [
      '업로드 이미지 경로는 API_BASE_URL을 붙인다',
      ['/v1/products/p/images/i'],
      [`${API_BASE_URL}/v1/products/p/images/i`],
    ],
    ['외부 URL은 그대로', ['https://x/a.jpg'], ['https://x/a.jpg']],
    ['빈 배열은 빈 배열', [], []],
    // 허용 밖 주소는 버린다(F17, 오케스트레이터 결정): 이미지 없음 → .ph 대체
    ['http: 절대 URL은 버린다', ['http://x/a.jpg'], []],
    ['data: URL은 버린다', ['data:image/png;base64,AAAA'], []],
    ['javascript: URL은 버린다', ['javascript:alert(1)'], []],
    ['프로토콜 상대 //host/x는 버린다', ['//evil.com/x.jpg'], []],
    ['파싱 불가 주소는 버린다', ['https://'], []],
    ['상대 경로가 아닌 문자열은 버린다', ['images/a.jpg'], []],
    [
      '허용·불허가 섞이면 허용만 남는다',
      ['http://x/a.jpg', '/v1/products/p/images/i', '//evil.com/x', 'https://x/b.jpg'],
      [`${API_BASE_URL}/v1/products/p/images/i`, 'https://x/b.jpg'],
    ],
  ])('product_image: %s', async (_name, images, urls) => {
    request.mockResolvedValue(detailDto({ product_image: images }));
    const detail = await repo.findById('o1');
    expect(detail.imageUrls).toEqual(urls);
  });

  it('404면 ApiError(status 404)를 그대로 throw', async () => {
    request.mockRejectedValue(new ApiError(404, 'OFFER_NOT_FOUND', 'not found'));
    await expect(repo.findById('o1')).rejects.toMatchObject({ status: 404 });
    await expect(repo.findById('o1')).rejects.toBeInstanceOf(ApiError);
  });
});
