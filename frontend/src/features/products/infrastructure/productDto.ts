import type { Product, ProductImage, ProductPage } from '@/entities/product';

type ProductDto = {
  id: string;
  store_id: string;
  name: string;
  category: string | null;
  description: string | null;
  original_price: number;
  is_active: boolean;
  product_image: string[] | null;
};

type ProductListDto = { items: ProductDto[]; page: number; size: number; total: number };

export type { ProductDto, ProductListDto };

export function toImageSrc(url: string, apiBase: string): string {
  // 프로토콜 상대 주소(//host)와 백슬래시 우회(/\\host)는 외부 주소가 되므로 그리지 않는다 (F17, D-24)
  if (url.startsWith('//') || url.startsWith('/\\')) return '';
  if (url.startsWith('/')) return apiBase + url;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  return ''; // javascript:·data: 등은 그리지 않는다 (F17)
}

export function toImages(urls: string[], apiBase: string): ProductImage[] {
  return urls.map((url) => ({ url, src: toImageSrc(url, apiBase) }));
}

export function toProduct(d: ProductDto, apiBase: string): Product {
  return {
    id: d.id,
    storeId: d.store_id,
    name: d.name,
    category: d.category,
    description: d.description,
    originalPrice: d.original_price,
    isActive: d.is_active,
    images: toImages(d.product_image ?? [], apiBase),
  };
}

export function toProductPage(d: ProductListDto, apiBase: string): ProductPage {
  return {
    items: d.items.map((item) => toProduct(item, apiBase)),
    page: d.page,
    size: d.size,
    total: d.total,
  };
}
