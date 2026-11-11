import { describe, expect, it } from 'vitest';
import {
  toImageSrc,
  toProduct,
  toProductPage,
  type ProductDto,
} from '@/features/products/infrastructure/productDto';

const dto: ProductDto = {
  id: 'p1',
  store_id: 'st-1',
  name: '식빵 모둠 5종',
  category: '빵',
  description: '오늘 구운 식빵',
  original_price: 12000,
  is_active: true,
  product_image: ['/v1/products/p1/images/i1'],
};

describe('features/products infrastructure productDto', () => {
  describe('toProduct', () => {
    it('snake_case를 camelCase로 바꾼다(is_active 포함)', () => {
      expect(toProduct(dto, '')).toEqual({
        id: 'p1',
        storeId: 'st-1',
        name: '식빵 모둠 5종',
        category: '빵',
        description: '오늘 구운 식빵',
        originalPrice: 12000,
        isActive: true,
        images: [{ url: '/v1/products/p1/images/i1', src: '/v1/products/p1/images/i1' }],
      });
    });

    it('is_active가 false이면 isActive도 false', () => {
      expect(toProduct({ ...dto, is_active: false }, '').isActive).toBe(false);
    });

    it('product_image가 null이면 images는 []', () => {
      expect(toProduct({ ...dto, product_image: null }, '').images).toEqual([]);
    });

    it('src가 빈 문자열이 되는 이미지도 images에 남긴다(url 보존)', () => {
      const p = toProduct({ ...dto, product_image: ['javascript:alert(1)'] }, '');
      expect(p.images).toEqual([{ url: 'javascript:alert(1)', src: '' }]);
    });

    it('// 주소 이미지는 src가 빈 문자열이고 url은 원본을 유지한다(A1)', () => {
      const p = toProduct({ ...dto, product_image: ['//evil.example/a.png'] }, 'https://api.x');
      expect(p.images).toEqual([{ url: '//evil.example/a.png', src: '' }]);
    });

    it('apiBase를 상대 경로 src 앞에 붙이되 url은 원본을 유지한다', () => {
      const p = toProduct(dto, 'https://api.x');
      expect(p.images[0]).toEqual({
        url: '/v1/products/p1/images/i1',
        src: 'https://api.x/v1/products/p1/images/i1',
      });
    });
  });

  describe('toImageSrc', () => {
    it('apiBase가 비면 상대 경로 그대로', () => {
      expect(toImageSrc('/v1/products/p1/images/i1', '')).toBe('/v1/products/p1/images/i1');
    });

    it('apiBase가 있으면 앞에 붙인다', () => {
      expect(toImageSrc('/v1/products/p1/images/i1', 'https://api.x')).toBe(
        'https://api.x/v1/products/p1/images/i1',
      );
    });

    it('http(s) 주소는 그대로', () => {
      expect(toImageSrc('https://example.com/a.jpg', 'https://api.x')).toBe(
        'https://example.com/a.jpg',
      );
      expect(toImageSrc('http://example.com/a.jpg', '')).toBe('http://example.com/a.jpg');
    });

    it.each(['javascript:alert(1)', 'data:image/png;base64,AAAA', ''])('%j → 빈 문자열', (url) => {
      expect(toImageSrc(url, 'https://api.x')).toBe('');
    });

    // A1: 프로토콜 상대 주소(//, /\)는 다른 호스트를 가리키므로 무시한다
    it.each(['//evil.example/a.png', '/\\evil.example/a.png', '//'])(
      '%j → 빈 문자열(apiBase가 비어도, 있어도)',
      (url) => {
        expect(toImageSrc(url, '')).toBe('');
        expect(toImageSrc(url, 'https://api.x')).toBe('');
      },
    );

    it('정상 상대 경로는 여전히 apiBase를 붙인다(A1 회귀 방지)', () => {
      expect(toImageSrc('/v1/products/p1/images/i1', 'https://api.x')).toBe(
        'https://api.x/v1/products/p1/images/i1',
      );
    });
  });

  describe('toProductPage', () => {
    it('items·page·size·total을 매핑한다', () => {
      const page = toProductPage({ items: [dto], page: 1, size: 100, total: 130 }, '');
      expect(page.page).toBe(1);
      expect(page.size).toBe(100);
      expect(page.total).toBe(130);
      expect(page.items).toEqual([toProduct(dto, '')]);
    });
  });
});
