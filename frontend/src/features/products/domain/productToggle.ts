import type { Product } from '@/entities/product';

/** 서버가 "이미 원하는 상태"라고 답한 오류 코드면 그 상태의 Product, 아니면 null. */
export function productWhenAlready(product: Product, errorCode: string): Product | null {
  if (errorCode === 'PRODUCT_ALREADY_INACTIVE') return { ...product, isActive: false };
  if (errorCode === 'PRODUCT_ALREADY_ACTIVE') return { ...product, isActive: true };
  return null;
}
