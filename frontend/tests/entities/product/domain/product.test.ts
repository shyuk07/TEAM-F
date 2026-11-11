import { describe, expect, it } from 'vitest';
import {
  formatProductPrice,
  primaryImage,
  productStatusLabel,
  productStatusTone,
  productSubtitle,
  uploadedImageId,
} from '@/entities/product';
import { baguetteProduct, breadProduct, noCategoryProduct } from '../fakes/products';

describe('entities/product domain', () => {
  describe('productStatusLabel · productStatusTone', () => {
    it('노출 상품 → 「노출」 / ok', () => {
      expect(productStatusLabel(breadProduct)).toBe('노출');
      expect(productStatusTone(breadProduct)).toBe('ok');
    });

    it('숨김 상품 → 「숨김」 / mute', () => {
      expect(productStatusLabel(baguetteProduct)).toBe('숨김');
      expect(productStatusTone(baguetteProduct)).toBe('mute');
    });
  });

  describe('formatProductPrice', () => {
    it.each([
      [0, '0원'],
      [999, '999원'],
      [1000, '1,000원'],
      [12000, '12,000원'],
      [99999999, '99,999,999원'],
    ])('%i → %s', (price, expected) => {
      expect(formatProductPrice(price)).toBe(expected);
    });
  });

  describe('productSubtitle', () => {
    it('카테고리가 있으면 「빵 · 12,000원」', () => {
      expect(productSubtitle(breadProduct)).toBe('빵 · 12,000원');
    });

    it('카테고리가 null이면 「12,000원」', () => {
      expect(productSubtitle(noCategoryProduct)).toBe('12,000원');
    });

    it('카테고리가 빈 문자열이면 「12,000원」', () => {
      expect(productSubtitle({ ...noCategoryProduct, category: '' })).toBe('12,000원');
    });
  });

  describe('primaryImage', () => {
    it('이미지 0장 → null', () => {
      expect(primaryImage(baguetteProduct)).toBeNull();
    });

    it('2장이면 첫 장', () => {
      const second = { url: '/v1/products/p1/images/i2', src: '/v1/products/p1/images/i2' };
      const p = { ...breadProduct, images: [...breadProduct.images, second] };
      expect(primaryImage(p)).toBe(breadProduct.images[0]);
    });
  });

  describe('uploadedImageId', () => {
    it('같은 상품의 업로드 주소는 id를 돌려준다', () => {
      expect(uploadedImageId('p1', '/v1/products/p1/images/i1')).toBe('i1');
    });

    it.each([
      ['다른 상품 id', '/v1/products/p9/images/i1'],
      ['외부 URL', 'https://example.com/a.jpg'],
      ['id가 빈 주소', '/v1/products/p1/images/'],
      ['빈 문자열', ''],
    ])('%s → null', (_label, url) => {
      expect(uploadedImageId('p1', url)).toBeNull();
    });
  });
});
