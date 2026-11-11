import { describe, expect, it } from 'vitest';
import { diffProduct, hasChanges } from '@/features/products/domain/productChanges';
import type { ProductFormValue } from '@/features/products/domain/productForm';
import { breadProduct, noCategoryProduct } from '../../../entities/product/fakes/products';

const same: ProductFormValue = {
  name: breadProduct.name,
  originalPrice: breadProduct.originalPrice,
  category: breadProduct.category,
  description: breadProduct.description,
};

describe('features/products domain productChanges', () => {
  it('같은 값이면 diffProduct는 {}이고 hasChanges는 false', () => {
    const c = diffProduct(breadProduct, same);
    expect(c).toEqual({});
    expect(hasChanges(c)).toBe(false);
  });

  it('이름만 다르면 {name}만', () => {
    expect(diffProduct(breadProduct, { ...same, name: '새 이름' })).toEqual({ name: '새 이름' });
  });

  it('가격만 다르면 {originalPrice}만', () => {
    expect(diffProduct(breadProduct, { ...same, originalPrice: 13000 })).toEqual({
      originalPrice: 13000,
    });
  });

  it('카테고리를 값 → null로 비우면 {category: null}', () => {
    expect(diffProduct(breadProduct, { ...same, category: null })).toEqual({ category: null });
  });

  it('카테고리가 원래 null이고 새 값도 null이면 키가 없다', () => {
    const value = { ...same, category: null, description: null };
    const c = diffProduct(noCategoryProduct, {
      ...value,
      name: noCategoryProduct.name,
      originalPrice: noCategoryProduct.originalPrice,
    });
    expect('category' in c).toBe(false);
  });

  it('설명을 값 → null로 비우면 {description: null}', () => {
    expect(diffProduct(breadProduct, { ...same, description: null })).toEqual({
      description: null,
    });
  });

  it('설명이 원래 null이고 새 값도 null이면 키가 없다', () => {
    const c = diffProduct(noCategoryProduct, {
      name: noCategoryProduct.name,
      originalPrice: noCategoryProduct.originalPrice,
      category: null,
      description: null,
    });
    expect('description' in c).toBe(false);
    expect(c).toEqual({});
  });

  it('카테고리·설명이 안 바뀌면 두 키 모두 없다', () => {
    const c = diffProduct(breadProduct, { ...same, name: '새 이름', originalPrice: 1 });
    expect('category' in c).toBe(false);
    expect('description' in c).toBe(false);
  });

  it('값이 null인 키는 category·description에서만 나온다(이름·가격은 항상 값)', () => {
    const c = diffProduct(breadProduct, {
      name: '새 이름',
      originalPrice: 1,
      category: null,
      description: null,
    });
    expect(c).toEqual({ name: '새 이름', originalPrice: 1, category: null, description: null });
    expect(c.name).not.toBeNull();
    expect(c.originalPrice).not.toBeNull();
  });

  it('값 → 다른 값이면 그 값이 담긴다(null이 아님)', () => {
    expect(diffProduct(breadProduct, { ...same, category: '케이크' })).toEqual({
      category: '케이크',
    });
  });

  it('hasChanges는 키가 하나라도 있으면 true(null 값 포함)', () => {
    expect(hasChanges({ name: 'x' })).toBe(true);
    expect(hasChanges({ category: null })).toBe(true);
  });
});
