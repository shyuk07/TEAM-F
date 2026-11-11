import type { Product } from '@/entities/product';
import { PRODUCT_ERROR_TEXT } from './productMessages';

export type ProductFormInput = {
  name: string;
  price: string;
  category: string;
  description: string;
};

export type ProductFormValue = {
  name: string;
  originalPrice: number;
  category: string | null;
  description: string | null;
};

export type ProductFormField = 'name' | 'price' | 'category';

export type ProductFormResult =
  | { ok: true; value: ProductFormValue }
  | { ok: false; errors: Partial<Record<ProductFormField, string>> };

export const NAME_MAX = 200;
export const CATEGORY_MAX = 80;
export const PRICE_MAX = 99_999_999;

// 쉼표·앞뒤 공백을 지운 뒤 숫자만이면 정수, 아니면 null
export function parsePrice(input: string): number | null {
  const cleaned = input.trim().replace(/,/g, '');
  if (!/^\d+$/.test(cleaned)) return null;
  return Number(cleaned);
}

export function validateProductForm(input: ProductFormInput): ProductFormResult {
  const errors: Partial<Record<ProductFormField, string>> = {};

  const name = input.name.trim();
  if (name.length < 1) errors.name = PRODUCT_ERROR_TEXT.nameRequired;
  else if (name.length > NAME_MAX) errors.name = PRODUCT_ERROR_TEXT.nameTooLong;

  const price = parsePrice(input.price);
  if (input.price.trim() === '') errors.price = PRODUCT_ERROR_TEXT.priceRequired;
  else if (price === null || price < 1 || price > PRICE_MAX) {
    errors.price = PRODUCT_ERROR_TEXT.priceRange;
  }

  const category = input.category.trim();
  if (category.length > CATEGORY_MAX) errors.category = PRODUCT_ERROR_TEXT.categoryTooLong;

  if (Object.keys(errors).length > 0 || price === null) return { ok: false, errors };

  const description = input.description.trim();
  return {
    ok: true,
    value: {
      name,
      originalPrice: price,
      category: category === '' ? null : category,
      description: description === '' ? null : description,
    },
  };
}

export function productFormFromProduct(p: Product): ProductFormInput {
  return {
    name: p.name,
    price: String(p.originalPrice),
    category: p.category ?? '',
    description: p.description ?? '',
  };
}
