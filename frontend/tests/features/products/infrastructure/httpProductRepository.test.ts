import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/shared/api/error';
import { HttpProductRepository } from '@/features/products/infrastructure/httpProductRepository';

// apiGet은 request로 위임하는 가짜라서 구현이 apiGet·request 어느 쪽을 써도 request 호출로 확인한다.
const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('@/shared/api/client', () => ({
  request,
  apiGet: (path: string, signal?: AbortSignal) => request(path, { signal }),
}));

const dto = {
  id: 'p1',
  store_id: 's1',
  name: '식빵 모둠 5종',
  category: '빵',
  description: null,
  original_price: 12000,
  is_active: true,
  product_image: ['/v1/products/p1/images/i1'],
};

const call = () => {
  const [path, opts] = request.mock.calls[0] as [
    string,
    { method?: string; signal?: AbortSignal }?,
  ];
  return { path, method: opts?.method ?? 'GET', signal: opts?.signal };
};

describe('features/products infrastructure HttpProductRepository', () => {
  beforeEach(() => {
    request.mockReset();
  });

  describe('findByStore', () => {
    it('GET /v1/stores/s1/products?page=1&size=100 (is_active 쿼리 없음)', async () => {
      request.mockResolvedValue({ items: [dto], page: 1, size: 100, total: 1 });
      await new HttpProductRepository().findByStore('s1');
      const { path, method } = call();
      expect(path).toBe('/v1/stores/s1/products?page=1&size=100');
      expect(method).toBe('GET');
      expect(path).not.toContain('is_active');
    });

    it('응답을 ProductPage로 바꾼다', async () => {
      request.mockResolvedValue({ items: [dto], page: 1, size: 100, total: 1 });
      const page = await new HttpProductRepository().findByStore('s1');
      expect(page.total).toBe(1);
      expect(page.items[0]).toMatchObject({
        id: 'p1',
        storeId: 's1',
        originalPrice: 12000,
        isActive: true,
      });
    });

    it('상점 id가 특수문자면 인코딩한다', async () => {
      request.mockResolvedValue({ items: [], page: 1, size: 100, total: 0 });
      await new HttpProductRepository().findByStore('a/b c');
      expect(call().path).toBe('/v1/stores/a%2Fb%20c/products?page=1&size=100');
    });

    it('signal을 요청에 전달한다', async () => {
      request.mockResolvedValue({ items: [], page: 1, size: 100, total: 0 });
      const ctrl = new AbortController();
      await new HttpProductRepository().findByStore('s1', ctrl.signal);
      expect(call().signal).toBe(ctrl.signal);
    });

    it('ApiError는 그대로 던진다', async () => {
      request.mockRejectedValue(new ApiError(500, 'UNKNOWN', 'x'));
      await expect(new HttpProductRepository().findByStore('s1')).rejects.toMatchObject({
        status: 500,
        errorCode: 'UNKNOWN',
      });
    });
  });

  describe('findById', () => {
    it('GET /v1/products/p1', async () => {
      request.mockResolvedValue(dto);
      const product = await new HttpProductRepository().findById('p1');
      const { path, method } = call();
      expect(path).toBe('/v1/products/p1');
      expect(method).toBe('GET');
      expect(product.name).toBe('식빵 모둠 5종');
    });

    it('id를 인코딩한다', async () => {
      request.mockResolvedValue(dto);
      await new HttpProductRepository().findById('a/b');
      expect(call().path).toBe('/v1/products/a%2Fb');
    });

    it('ApiError(404)는 그대로 던진다', async () => {
      request.mockRejectedValue(new ApiError(404, 'NOT_FOUND', 'x'));
      await expect(new HttpProductRepository().findById('p1')).rejects.toMatchObject({
        status: 404,
        errorCode: 'NOT_FOUND',
      });
    });
  });
});
