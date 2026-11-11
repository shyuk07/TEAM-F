import type { Product } from '@/entities/product';

export const breadProduct: Product = {
  id: 'p1',
  storeId: 'st-1',
  name: '식빵 모둠 5종',
  category: '빵',
  description: '오늘 구운 식빵',
  originalPrice: 12000,
  isActive: true,
  images: [{ url: '/v1/products/p1/images/i1', src: '/v1/products/p1/images/i1' }],
};

export const baguetteProduct: Product = {
  id: 'p2',
  storeId: 'st-1',
  name: '바게트',
  category: '빵',
  description: null,
  originalPrice: 4000,
  isActive: false,
  images: [],
};

export const noCategoryProduct: Product = {
  id: 'p3',
  storeId: 'st-1',
  name: '단팥빵',
  category: null,
  description: null,
  originalPrice: 12000,
  isActive: true,
  images: [],
};

/** 등록 성공 응답으로 쓰는 새 상품. */
export const createdProduct: Product = {
  id: 'p-new',
  storeId: 'st-1',
  name: '식빵',
  category: null,
  description: null,
  originalPrice: 12000,
  isActive: true,
  images: [],
};
