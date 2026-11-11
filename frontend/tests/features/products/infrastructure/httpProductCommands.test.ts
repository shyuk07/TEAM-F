import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ProductChanges } from '@/features/products/domain/productChanges';
import { HttpProductCommands } from '@/features/products/infrastructure/httpProductCommands';

// apiPost는 request로 위임하는 가짜라서 구현이 apiPost·request 어느 쪽을 써도 request 호출로 확인한다.
const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock('@/shared/api/client', () => ({
  request,
  apiGet: (path: string, signal?: AbortSignal) => request(path, { signal }),
  apiPost: (path: string, body?: unknown, signal?: AbortSignal) =>
    request(path, { method: 'POST', body, signal }),
}));

const dto = {
  id: 'p1',
  store_id: 's1',
  name: '식빵',
  category: null,
  description: null,
  original_price: 12000,
  is_active: true,
  product_image: [],
};

type Call = { path: string; method: string; body: unknown };
const lastCall = (): Call => {
  const [path, opts] = request.mock.calls[request.mock.calls.length - 1] as [
    string,
    { method?: string; body?: unknown }?,
  ];
  return { path, method: opts?.method ?? 'GET', body: opts?.body };
};
const formOf = (): FormData => {
  const { body } = lastCall();
  expect(body).toBeInstanceOf(FormData);
  return body as FormData;
};
const jsonOf = (): Record<string, unknown> => lastCall().body as Record<string, unknown>;

const commands = () => new HttpProductCommands();

describe('features/products infrastructure HttpProductCommands', () => {
  beforeEach(() => {
    request.mockReset();
    request.mockResolvedValue(dto);
  });

  describe('create', () => {
    const input = { name: '식빵', originalPrice: 12000, category: null, description: null };

    it('POST /v1/stores/s1/products, body는 FormData', async () => {
      await commands().create('s1', input, null);
      const { path, method } = lastCall();
      expect(path).toBe('/v1/stores/s1/products');
      expect(method).toBe('POST');
      expect(formOf()).toBeInstanceOf(FormData);
    });

    it('name과 original_price(문자열 "12000")가 들어간다', async () => {
      await commands().create('s1', input, null);
      const form = formOf();
      expect(form.get('name')).toBe('식빵');
      expect(form.get('original_price')).toBe('12000');
    });

    it('category·description이 null이면 키가 없다', async () => {
      await commands().create('s1', input, null);
      const form = formOf();
      expect(form.has('category')).toBe(false);
      expect(form.has('description')).toBe(false);
    });

    it('category·description에 값이 있으면 키가 있다', async () => {
      await commands().create('s1', { ...input, category: '빵', description: '설명' }, null);
      const form = formOf();
      expect(form.get('category')).toBe('빵');
      expect(form.get('description')).toBe('설명');
    });

    it('photo가 있으면 file로 보내고, 없으면 file 키가 없다', async () => {
      const photo = new File([new Uint8Array(3)], 'a.jpg', { type: 'image/jpeg' });
      await commands().create('s1', input, photo);
      expect(formOf().get('file')).toBeInstanceOf(Blob);
      await commands().create('s1', input, null);
      expect(formOf().has('file')).toBe(false);
    });

    it('product_image는 절대 보내지 않는다', async () => {
      const photo = new File([new Uint8Array(3)], 'a.jpg', { type: 'image/jpeg' });
      await commands().create('s1', { ...input, category: '빵' }, photo);
      expect(formOf().has('product_image')).toBe(false);
    });

    it('어떤 키의 문자열 값도 "null"이나 빈 문자열이 아니다(null 비전송)', async () => {
      await commands().create('s1', input, null);
      const strings = Array.from(formOf().values()).filter((v) => typeof v === 'string');
      expect(strings.length).toBeGreaterThan(0);
      expect(strings).not.toContain('null');
      expect(strings).not.toContain('');
    });

    it('응답을 Product로 바꿔 돌려준다', async () => {
      const product = await commands().create('s1', input, null);
      expect(product).toMatchObject({ id: 'p1', storeId: 's1', originalPrice: 12000 });
    });

    it('signal을 전달한다', async () => {
      const ctrl = new AbortController();
      await commands().create('s1', input, null, ctrl.signal);
      const opts = request.mock.calls[0][1] as { signal?: AbortSignal };
      expect(opts.signal).toBe(ctrl.signal);
    });
  });

  describe('update', () => {
    it('PATCH /v1/products/p1, originalPrice는 original_price로 바꾼다', async () => {
      await commands().update('p1', { name: '새 이름', originalPrice: 13000 });
      const { path, method } = lastCall();
      expect(path).toBe('/v1/products/p1');
      expect(method).toBe('PATCH');
      expect(jsonOf()).toEqual({ name: '새 이름', original_price: 13000 });
    });

    it('{category: null} → 본문 {category: null}', async () => {
      await commands().update('p1', { category: null });
      expect(jsonOf()).toEqual({ category: null });
    });

    it('{description: null} → 본문 {description: null}', async () => {
      await commands().update('p1', { description: null });
      expect(jsonOf()).toEqual({ description: null });
    });

    it('{name: "x"} → 본문 키가 name 하나뿐(category·description·product_image 없음)', async () => {
      await commands().update('p1', { name: 'x' });
      const body = jsonOf();
      expect(Object.keys(body)).toEqual(['name']);
      expect('category' in body).toBe(false);
      expect('description' in body).toBe(false);
      expect('product_image' in body).toBe(false);
    });

    it('응답을 Product로 바꿔 돌려준다', async () => {
      const product = await commands().update('p1', { name: 'x' });
      expect(product.id).toBe('p1');
    });

    // D-18: null은 category·description을 비울 때만 나간다.
    it.each<[string, ProductChanges, Record<string, unknown>]>([
      ['이름만', { name: '가' }, { name: '가' }],
      ['가격만', { originalPrice: 5000 }, { original_price: 5000 }],
      ['카테고리 값 변경', { category: '케이크' }, { category: '케이크' }],
      ['카테고리 비우기', { category: null }, { category: null }],
      [
        '설명 비우기 + 이름 변경',
        { name: '가', description: null },
        { name: '가', description: null },
      ],
    ])('null은 비우기 외에는 나가지 않는다: %s', async (_label, changes, expected) => {
      await commands().update('p1', changes);
      const body = jsonOf();
      expect(body).toEqual(expected);
      const cleared = Object.keys(changes).filter(
        (k) => (k === 'category' || k === 'description') && changes[k] === null,
      );
      const nullKeys = Object.entries(body)
        .filter(([, v]) => v === null)
        .map(([k]) => k);
      expect(nullKeys.sort()).toEqual(cleared.sort());
    });
  });

  describe('deactivate · activate', () => {
    it('deactivate → POST /v1/products/p1/deactivate, 본문 없음', async () => {
      await commands().deactivate('p1');
      const { path, method, body } = lastCall();
      expect(path).toBe('/v1/products/p1/deactivate');
      expect(method).toBe('POST');
      expect(body).toBeUndefined();
    });

    it('activate → POST /v1/products/p1/activate, 본문 없음', async () => {
      await commands().activate('p1');
      const { path, method, body } = lastCall();
      expect(path).toBe('/v1/products/p1/activate');
      expect(method).toBe('POST');
      expect(body).toBeUndefined();
    });

    it('응답을 Product로 바꿔 돌려준다', async () => {
      request.mockResolvedValue({ ...dto, is_active: false });
      const product = await commands().deactivate('p1');
      expect(product.isActive).toBe(false);
    });
  });
});
