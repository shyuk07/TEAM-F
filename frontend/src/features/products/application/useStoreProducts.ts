import { useDep } from '@/shared/lib/di';
import { useAsync, type AsyncState } from '@/shared/lib/useAsync';
import { ProductRepositoryToken, type ProductPage } from '@/entities/product';

export function useStoreProducts(storeId: string): AsyncState<ProductPage> & { reload(): void } {
  const repo = useDep(ProductRepositoryToken);
  return useAsync((signal) => repo.findByStore(storeId, signal), storeId);
}
