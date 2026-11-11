import type { Product, ProductPage } from './product';

export interface ProductRepository {
  /** GET /v1/stores/{storeId}/products?page=1&size=100 (is_active 미지정 → 본인 상점이면 노출·숨김 모두) */
  findByStore(storeId: string, signal?: AbortSignal): Promise<ProductPage>;
  /** GET /v1/products/{id}. 404·403은 ApiError로 던진다 */
  findById(productId: string, signal?: AbortSignal): Promise<Product>;
}
