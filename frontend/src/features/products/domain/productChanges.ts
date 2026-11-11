import type { Product } from '@/entities/product';
import type { ProductFormValue } from './productForm';

export type ProductChanges = {
  name?: string;
  originalPrice?: number;
  category?: string | null; // null은 "비우기"일 때만. 바뀌지 않았으면 키 자체가 없다
  description?: string | null; // 같음
};

// 달라진 필드만 담는다. null은 원래 값이 있었는데 비운 경우에만 나온다.
export function diffProduct(original: Product, value: ProductFormValue): ProductChanges {
  const changes: ProductChanges = {};
  if (value.name !== original.name) changes.name = value.name;
  if (value.originalPrice !== original.originalPrice) changes.originalPrice = value.originalPrice;
  if (value.category !== (original.category ?? null)) changes.category = value.category;
  if (value.description !== (original.description ?? null)) changes.description = value.description;
  return changes;
}

export function hasChanges(c: ProductChanges): boolean {
  return Object.keys(c).length > 0;
}
