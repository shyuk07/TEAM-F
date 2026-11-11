import { useDep } from '@/shared/lib/di';
import { useAsync, type AsyncState } from '@/shared/lib/useAsync';
import { readErrorInfo } from '@/shared/lib/errorInfo';
import { productLoadFailure, type ProductLoadFailure } from '../domain/productMessages';
import { ProductRepositoryToken, type Product } from '@/entities/product';

export function useProduct(
  productId: string,
): AsyncState<Product> & { reload(): void; failure: ProductLoadFailure | null } {
  const repo = useDep(ProductRepositoryToken);
  const state = useAsync((signal) => repo.findById(productId, signal), productId);
  const { reload } = state;
  return Object.assign(
    { ...state, reload },
    { failure: state.status === 'error' ? productLoadFailure(readErrorInfo(state.error)) : null },
  );
}
