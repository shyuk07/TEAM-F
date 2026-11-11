import type { Offer } from '../domain/offer';
import type { OfferCommands, StockAdjustResult } from '../domain/offerCommands';
import { signedAmount, validateStockAdjust, type StockMode } from '../domain/stockAdjustment';

export async function adjustStock(
  deps: { commands: OfferCommands },
  offer: Offer,
  mode: StockMode,
  amount: number,
  reason?: string,
  signal?: AbortSignal,
): Promise<StockAdjustResult> {
  const issue = validateStockAdjust(offer, mode, amount, reason);
  if (issue !== null) {
    throw new Error(`유효하지 않은 수량 조정: ${issue}`);
  }
  const signed = signedAmount(mode, amount);
  return deps.commands.adjustStock(offer.id, signed, reason, signal);
}
