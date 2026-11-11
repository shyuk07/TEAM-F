import { useDep } from '@/shared/lib/di';
import { readErrorInfo, type ErrorInfo } from '@/shared/lib/errorInfo';
import { useAsync } from '@/shared/lib/useAsync';
import type { Offer } from '../domain/offer';
import { OfferRepositoryToken } from './tokens';

export type OwnerOfferStatus = 'loading' | 'success' | 'error';

export function useOwnerOffer(offerId: string): {
  status: OwnerOfferStatus;
  offer: Offer | null;
  failure: ErrorInfo | null;
  reload: () => void;
} {
  const repo = useDep(OfferRepositoryToken);
  const state = useAsync((signal) => repo.findOfferById(offerId, signal), offerId);

  return {
    status: state.status,
    offer: state.data ?? null,
    failure: state.status === 'error' ? readErrorInfo(state.error) : null,
    reload: state.reload,
  };
}
