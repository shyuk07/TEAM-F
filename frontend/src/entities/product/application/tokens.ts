import { createToken } from '@/shared/lib/di';
import type { ProductRepository } from '../domain/productRepository';

export const ProductRepositoryToken = createToken<ProductRepository>('ProductRepository');
