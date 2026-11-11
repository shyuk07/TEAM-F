import { request } from '@/shared/api/client';
import { API_BASE_URL } from '@/shared/config/env';
import type { Product, ProductPage, ProductRepository } from '@/entities/product';
import { toProduct, toProductPage, type ProductDto, type ProductListDto } from './productDto';

// product entity 포트의 구현체. product 개체의 소유 영역은 products(F18, fsd-structure §1.1).
export class HttpProductRepository implements ProductRepository {
  // TODO: 상품을 한 번에 100개까지만 불러온다. 101번째부터는 목록에 나오지 않는다.
  //   왜: O4 명세에 더 보기·페이지 규칙이 없다 (docs/design/frontend/products.md D-15)
  //   언제: 결정 후 (사용자: 상품 100개 초과 처리)
  async findByStore(storeId: string, signal?: AbortSignal): Promise<ProductPage> {
    const dto = await request<ProductListDto>(
      `/v1/stores/${encodeURIComponent(storeId)}/products?page=1&size=100`,
      { signal },
    );
    return toProductPage(dto, API_BASE_URL);
  }

  async findById(productId: string, signal?: AbortSignal): Promise<Product> {
    const dto = await request<ProductDto>(`/v1/products/${encodeURIComponent(productId)}`, {
      signal,
    });
    return toProduct(dto, API_BASE_URL);
  }
}
