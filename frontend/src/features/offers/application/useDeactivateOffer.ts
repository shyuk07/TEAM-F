import { useCallback } from 'react';
import { useDep } from '@/shared/lib/di';
import type { DeactivateInput, DeactivateResult } from '../domain/offerCommands';
import { ownerOfferErrorMessage } from '../domain/ownerOfferMessages';
import { deactivateOffer } from './deactivateOffer';
import { OfferCommandsToken } from './tokens';
import { useOfferRun, type RunStatus } from './useOfferRun';

export function useDeactivateOffer(): {
  submit: (offerId: string, input: DeactivateInput) => Promise<DeactivateResult | null>;
  status: RunStatus;
  errorMessage: string | null;
  errorCode: string | null;
  reset: () => void;
} {
  const commands = useDep(OfferCommandsToken);
  const { run, status, errorMessage, errorCode, reset } = useOfferRun();

  const submit = useCallback(
    async (offerId: string, input: DeactivateInput): Promise<DeactivateResult | null> => {
      return run((signal) => deactivateOffer({ commands }, offerId, input, signal), {
        message: ownerOfferErrorMessage,
      });
    },
    [commands, run],
  );

  return { submit, status, errorMessage, errorCode, reset };
}
