import { useCallback } from 'react';
import { useDep } from '@/shared/lib/di';
import type { Offer } from '../domain/offer';
import type { OfferChanges } from '../domain/offerCommands';
import { hasChanges } from '../domain/offerEdit';
import { ownerOfferErrorMessage } from '../domain/ownerOfferMessages';
import { saveOffer } from './saveOffer';
import { OfferCommandsToken } from './tokens';
import { useOfferRun, type RunStatus } from './useOfferRun';

export function useSaveOffer(): {
  submit: (offerId: string, changes: OfferChanges) => Promise<Offer | null>;
  status: RunStatus;
  errorMessage: string | null;
  errorCode: string | null;
  isLocked: boolean;
  reset: () => void;
} {
  const commands = useDep(OfferCommandsToken);
  const { run, status, errorMessage, errorCode, reset } = useOfferRun();

  const submit = useCallback(
    async (offerId: string, changes: OfferChanges): Promise<Offer | null> => {
      if (!hasChanges(changes)) {
        return null;
      }
      return run((signal) => saveOffer({ commands }, offerId, changes, signal), {
        message: ownerOfferErrorMessage,
      });
    },
    [commands, run],
  );

  const isLocked = errorCode === 'OFFER_HAS_RESERVATIONS';

  return { submit, status, errorMessage, errorCode, isLocked, reset };
}
