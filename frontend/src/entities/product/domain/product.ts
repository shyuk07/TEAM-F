import { groupDigits } from '@/shared/lib/format';

export type ProductImage = {
  url: string; // 서버가 준 원본 주소. 저장(PATCH)할 때 그대로 되돌려 보낸다
  src: string; // <img src>용. 상대 경로면 API_BASE_URL을 붙인 주소 (infrastructure가 계산)
};

export type Product = {
  id: string;
  storeId: string;
  name: string;
  category: string | null;
  description: string | null;
  originalPrice: number;
  isActive: boolean;
  images: ProductImage[];
};

export type ProductPage = { items: Product[]; page: number; size: number; total: number };

export function productStatusLabel(p: Product): '노출' | '숨김' {
  return p.isActive ? '노출' : '숨김';
}

export function productStatusTone(p: Product): 'ok' | 'mute' {
  return p.isActive ? 'ok' : 'mute';
}

export function formatProductPrice(price: number): string {
  return `${groupDigits(price)}원`;
}

export function productSubtitle(p: Product): string {
  const price = formatProductPrice(p.originalPrice);
  return p.category ? `${p.category} · ${price}` : price;
}

export function primaryImage(p: Product): ProductImage | null {
  return p.images[0] ?? null;
}

export function uploadedImageId(productId: string, url: string): string | null {
  const prefix = `/v1/products/${productId}/images/`;
  if (!url.startsWith(prefix)) return null;
  const id = url.slice(prefix.length);
  return id === '' ? null : id;
}
