import { ProductRepositoryToken, type Product } from '@/entities/product';
import { useDep } from '@/shared/lib/di';
import { useAsync } from '@/shared/lib/useAsync';

export type SellableProductsStatus = 'loading' | 'success' | 'error';

export function useSellableProducts(storeId: string): {
  status: SellableProductsStatus;
  products: Product[];
  reload: () => void;
} {
  const repo = useDep(ProductRepositoryToken);
  const state = useAsync(async (signal) => {
    if (!storeId) return [];
    const page = await repo.findByStore(storeId, signal);
    return page.items.filter((p) => p.isActive);
  }, storeId);

  return {
    status: state.status,
    products: state.data ?? [],
    reload: state.reload,
  };
}
