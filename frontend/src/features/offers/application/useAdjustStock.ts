import { useCallback } from 'react';
import { useDep } from '@/shared/lib/di';
import type { Offer } from '../domain/offer';
import type { StockAdjustResult } from '../domain/offerCommands';
import { ownerOfferErrorMessage } from '../domain/ownerOfferMessages';
import type { StockMode } from '../domain/stockAdjustment';
import { adjustStock } from './adjustStock';
import { OfferCommandsToken } from './tokens';
import { useOfferRun, type RunStatus } from './useOfferRun';

export function useAdjustStock(): {
  submit: (
    offer: Offer,
    mode: StockMode,
    amount: number,
    reason?: string,
  ) => Promise<StockAdjustResult | null>;
  status: RunStatus;
  errorMessage: string | null;
  errorCode: string | null;
  reset: () => void;
} {
  const commands = useDep(OfferCommandsToken);
  const { run, status, errorMessage, errorCode, reset } = useOfferRun();

  const submit = useCallback(
    async (
      offer: Offer,
      mode: StockMode,
      amount: number,
      reason?: string,
    ): Promise<StockAdjustResult | null> => {
      return run((signal) => adjustStock({ commands }, offer, mode, amount, reason, signal), {
        message: ownerOfferErrorMessage,
      });
    },
    [commands, run],
  );

  return { submit, status, errorMessage, errorCode, reset };
}
