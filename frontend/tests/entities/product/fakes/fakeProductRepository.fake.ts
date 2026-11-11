import { vi } from 'vitest';
import type { ProductRepository } from '@/entities/product';
import { baguetteProduct, breadProduct } from './products';

export class FakeProductRepository implements ProductRepository {
  findByStore = vi.fn<ProductRepository['findByStore']>(() =>
    Promise.resolve({ items: [breadProduct, baguetteProduct], page: 1, size: 100, total: 2 }),
  );
  findById = vi.fn<ProductRepository['findById']>(() => Promise.resolve(breadProduct));
}
