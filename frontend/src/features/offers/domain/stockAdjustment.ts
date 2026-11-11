import type { Offer } from './offer';

export type StockMode = 'subtract' | 'add';

export const STOCK_REASON_MAX = 200;
export const STOCK_MAX = 9999;

export function amountBounds(
  offer: Offer,
  mode: StockMode,
): {
  min: number;
  max: number;
} {
  if (mode === 'subtract') {
    return { min: 1, max: Math.max(0, offer.remainingStock) };
  }
  return { min: 1, max: Math.max(0, STOCK_MAX - offer.initialStock) };
}

export function signedAmount(mode: StockMode, amount: number): number {
  return mode === 'subtract' ? -amount : amount;
}

export function stockAfter(offer: Offer, mode: StockMode, amount: number): number {
  return offer.remainingStock + signedAmount(mode, amount);
}

export type StockIssue = 'amount-zero' | 'over-remaining' | 'over-max' | 'reason-too-long';

export function validateStockAdjust(
  offer: Offer,
  mode: StockMode,
  amount: number,
  reason?: string,
): StockIssue | null {
  if (amount < 1) {
    return 'amount-zero';
  }
  if (mode === 'subtract' && amount > offer.remainingStock) {
    return 'over-remaining';
  }
  if (mode === 'add' && offer.initialStock + amount > STOCK_MAX) {
    return 'over-max';
  }
  if (reason && reason.length > STOCK_REASON_MAX) {
    return 'reason-too-long';
  }
  return null;
}
