import type { Product } from '@/entities/product';
import type { ProductChanges } from './productChanges';

export type NewProduct = {
  name: string;
  originalPrice: number;
  category: string | null;
  description: string | null;
};

export interface ProductCommands {
  /** POST /v1/stores/{storeId}/products (multipart, photo 있으면 file 포함). 사진과 상품은 한 요청 */
  create(
    storeId: string,
    input: NewProduct,
    photo: Blob | null,
    signal?: AbortSignal,
  ): Promise<Product>;
  /** PATCH /v1/products/{id}. changes의 키만 보낸다. null은 category·description을 비울 때만 나간다 */
  update(productId: string, changes: ProductChanges, signal?: AbortSignal): Promise<Product>;
  /** POST /v1/products/{id}/deactivate */
  deactivate(productId: string, signal?: AbortSignal): Promise<Product>;
  /** POST /v1/products/{id}/activate */
  activate(productId: string, signal?: AbortSignal): Promise<Product>;
}
