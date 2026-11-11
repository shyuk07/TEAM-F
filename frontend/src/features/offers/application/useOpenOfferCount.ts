import { useDep } from '@/shared/lib/di';
import { useAsync } from '@/shared/lib/useAsync';
import { OfferRepositoryToken } from './tokens';

export function useOpenOfferCount(storeId: string): {
  status: 'loading' | 'success' | 'error';
  count: number;
} {
  const repo = useDep(OfferRepositoryToken);
  const state = useAsync(async (signal) => {
    if (!storeId) return 0;
    const res = await repo.findByStore(
      storeId,
      ['SCHEDULED', 'ON_SALE', 'SOLD_OUT', 'SUSPENDED'],
      1,
      1,
      signal,
    );
    return res.total;
  }, storeId);

  return {
    status: state.status,
    count: state.data ?? 0,
  };
}
