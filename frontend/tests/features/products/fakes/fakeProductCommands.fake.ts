import { vi } from 'vitest';
import type { ProductCommands } from '@/features/products/domain/productCommands';
import { breadProduct, createdProduct } from '../../../entities/product/fakes/products';

export class FakeProductCommands implements ProductCommands {
  create = vi.fn<ProductCommands['create']>(() => Promise.resolve(createdProduct));
  update = vi.fn<ProductCommands['update']>(() => Promise.resolve(breadProduct));
  deactivate = vi.fn<ProductCommands['deactivate']>(() =>
    Promise.resolve({ ...breadProduct, isActive: false }),
  );
  activate = vi.fn<ProductCommands['activate']>(() =>
    Promise.resolve({ ...breadProduct, isActive: true }),
  );
}
