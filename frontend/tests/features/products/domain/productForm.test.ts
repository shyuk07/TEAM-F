import { describe, expect, it } from 'vitest';
import {
  parsePrice,
  productFormFromProduct,
  validateProductForm,
  type ProductFormInput,
} from '@/features/products/domain/productForm';
import { breadProduct, noCategoryProduct } from '../../../entities/product/fakes/products';

const valid: ProductFormInput = {
  name: '식빵 모둠 5종',
  price: '12,000',
  category: '빵',
  description: '오늘 구운 식빵',
};

function errorsOf(input: ProductFormInput) {
  const r = validateProductForm(input);
  return r.ok ? null : r.errors;
}

describe('features/products domain productForm', () => {
  it('정상 입력은 ok이고 값으로 바뀐다', () => {
    expect(validateProductForm(valid)).toEqual({
      ok: true,
      value: {
        name: '식빵 모둠 5종',
        originalPrice: 12000,
        category: '빵',
        description: '오늘 구운 식빵',
      },
    });
  });

  describe('이름', () => {
    it.each(['', '   '])('%j → errors.name', (name) => {
      expect(errorsOf({ ...valid, name })).toHaveProperty('name');
    });

    it('1자와 200자는 ok', () => {
      expect(validateProductForm({ ...valid, name: 'a' }).ok).toBe(true);
      expect(validateProductForm({ ...valid, name: 'a'.repeat(200) }).ok).toBe(true);
    });

    it('201자는 errors.name', () => {
      expect(errorsOf({ ...valid, name: 'a'.repeat(201) })).toHaveProperty('name');
    });

    it('앞뒤 공백은 제거되어 값에 반영된다', () => {
      const r = validateProductForm({ ...valid, name: '  식빵  ' });
      expect(r.ok && r.value.name).toBe('식빵');
    });
  });

  describe('가격', () => {
    it('빈 값은 필수 오류(errors.price)', () => {
      expect(errorsOf({ ...valid, price: '' })).toHaveProperty('price');
    });

    it.each(['0', '100000000', '12a', '1.5', '-1'])('%j → errors.price', (price) => {
      expect(errorsOf({ ...valid, price })).toHaveProperty('price');
    });

    it.each([
      ['1', 1],
      ['99999999', 99999999],
      [' 12,000 ', 12000],
    ])('%j → %i', (price, expected) => {
      const r = validateProductForm({ ...valid, price });
      expect(r.ok && r.value.originalPrice).toBe(expected);
    });
  });

  describe('카테고리', () => {
    it.each(['', '  '])('%j → 값 null, 오류 없음', (category) => {
      const r = validateProductForm({ ...valid, category });
      expect(r.ok).toBe(true);
      expect(r.ok && r.value.category).toBeNull();
    });

    it('80자는 ok, 81자는 errors.category', () => {
      expect(validateProductForm({ ...valid, category: 'a'.repeat(80) }).ok).toBe(true);
      expect(errorsOf({ ...valid, category: 'a'.repeat(81) })).toHaveProperty('category');
    });
  });

  it('설명이 비면 값 null', () => {
    const r = validateProductForm({ ...valid, description: '   ' });
    expect(r.ok && r.value.description).toBeNull();
  });

  it('오류가 여러 칸이면 errors에 모두 담긴다', () => {
    const errors = errorsOf({ name: '', price: 'abc', category: 'a'.repeat(81), description: '' });
    expect(Object.keys(errors ?? {}).sort()).toEqual(['category', 'name', 'price']);
  });

  describe('parsePrice', () => {
    it.each([
      ['12,000', 12000],
      ['abc', null],
      ['', null],
      ['007', 7],
    ])('%j → %s', (input, expected) => {
      expect(parsePrice(input)).toBe(expected);
    });
  });

  describe('productFormFromProduct', () => {
    it('카테고리·설명이 null이면 빈 문자열, 가격은 쉼표 없는 숫자 문자열', () => {
      expect(productFormFromProduct(noCategoryProduct)).toEqual({
        name: '단팥빵',
        price: '12000',
        category: '',
        description: '',
      });
    });

    it('값이 있으면 그대로 채운다', () => {
      expect(productFormFromProduct(breadProduct)).toEqual({
        name: '식빵 모둠 5종',
        price: '12000',
        category: '빵',
        description: '오늘 구운 식빵',
      });
    });
  });
});
