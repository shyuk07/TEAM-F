import { useCallback } from 'react';
import { useDep } from '@/shared/lib/di';
import type { Offer } from '../domain/offer';
import { ownerOfferErrorMessage } from '../domain/ownerOfferMessages';
import { createOffer, type CreateOfferInput } from './createOffer';
import { OfferCommandsToken } from './tokens';
import { useOfferRun, type RunStatus } from './useOfferRun';

export function useCreateOffer(): {
  submit: (input: CreateOfferInput) => Promise<Offer | null>;
  status: RunStatus;
  errorMessage: string | null;
  errorCode: string | null;
  reset: () => void;
} {
  const commands = useDep(OfferCommandsToken);
  const { run, status, errorMessage, errorCode, reset } = useOfferRun();

  const submit = useCallback(
    async (input: CreateOfferInput): Promise<Offer | null> => {
      return run((signal) => createOffer({ commands }, input, signal), {
        message: ownerOfferErrorMessage,
      });
    },
    [commands, run],
  );

  return { submit, status, errorMessage, errorCode, reset };
}
