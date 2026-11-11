import { request } from '@/shared/api/client';
import { API_BASE_URL } from '@/shared/config/env';
import type { Product } from '@/entities/product';
import type { ProductChanges } from '../domain/productChanges';
import type { NewProduct, ProductCommands } from '../domain/productCommands';
import { toProduct, type ProductDto } from './productDto';

const productPath = (productId: string) => `/v1/products/${encodeURIComponent(productId)}`;

export class HttpProductCommands implements ProductCommands {
  // 항상 multipart. 값이 없는 category·description·file은 키를 생략한다(null을 보내지 않는다).
  async create(
    storeId: string,
    input: NewProduct,
    photo: Blob | null,
    signal?: AbortSignal,
  ): Promise<Product> {
    const form = new FormData();
    form.append('name', input.name);
    form.append('original_price', String(input.originalPrice));
    if (input.category !== null && input.category !== '') form.append('category', input.category);
    if (input.description !== null && input.description !== '') {
      form.append('description', input.description);
    }
    if (photo !== null) form.append('file', photo);
    const dto = await request<ProductDto>(`/v1/stores/${encodeURIComponent(storeId)}/products`, {
      method: 'POST',
      body: form,
      signal,
    });
    return toProduct(dto, API_BASE_URL);
  }

  // changes의 키만 보낸다. null은 category·description을 비울 때만 담겨 있다.
  async update(productId: string, changes: ProductChanges, signal?: AbortSignal): Promise<Product> {
    const body: Record<string, unknown> = {};
    if (changes.name !== undefined) body.name = changes.name;
    if (changes.originalPrice !== undefined) body.original_price = changes.originalPrice;
    if (changes.category !== undefined) body.category = changes.category;
    if (changes.description !== undefined) body.description = changes.description;
    const dto = await request<ProductDto>(productPath(productId), {
      method: 'PATCH',
      body,
      signal,
    });
    return toProduct(dto, API_BASE_URL);
  }

  async deactivate(productId: string, signal?: AbortSignal): Promise<Product> {
    const dto = await request<ProductDto>(`${productPath(productId)}/deactivate`, {
      method: 'POST',
      signal,
    });
    return toProduct(dto, API_BASE_URL);
  }

  async activate(productId: string, signal?: AbortSignal): Promise<Product> {
    const dto = await request<ProductDto>(`${productPath(productId)}/activate`, {
      method: 'POST',
      signal,
    });
    return toProduct(dto, API_BASE_URL);
  }
}
