import { describe, expect, it } from 'vitest';
import { productWhenAlready } from '@/features/products/domain/productToggle';
import { baguetteProduct, breadProduct } from '../../../entities/product/fakes/products';

// B1(D-33): 서버가 "이미 원하는 상태"라고 답하면 그 상태의 Product를 돌려준다
describe('features/products domain productToggle', () => {
  it('PRODUCT_ALREADY_INACTIVE → isActive:false 상품, 다른 필드는 그대로', () => {
    expect(productWhenAlready(breadProduct, 'PRODUCT_ALREADY_INACTIVE')).toEqual({
      ...breadProduct,
      isActive: false,
    });
  });

  it('PRODUCT_ALREADY_ACTIVE → isActive:true 상품, 다른 필드는 그대로', () => {
    expect(productWhenAlready(baguetteProduct, 'PRODUCT_ALREADY_ACTIVE')).toEqual({
      ...baguetteProduct,
      isActive: true,
    });
  });

  it.each(['PRODUCT_HAS_OPEN_OFFER', 'STORE_CLOSED', 'UNKNOWN'])('%s → null', (code) => {
    expect(productWhenAlready(breadProduct, code)).toBeNull();
  });

  it('이름·가격·사진 등 다른 필드를 바꾸지 않는다', () => {
    const r = productWhenAlready(breadProduct, 'PRODUCT_ALREADY_INACTIVE');
    expect(r?.name).toBe(breadProduct.name);
    expect(r?.originalPrice).toBe(breadProduct.originalPrice);
    expect(r?.images).toEqual(breadProduct.images);
  });
});
