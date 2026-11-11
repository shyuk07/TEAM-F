export const MAX_QUANTITY = 5;
export const MIN_QUANTITY = 1;

export function maxQuantity(remainingStock: number): number {
  return Math.max(0, Math.min(remainingStock, MAX_QUANTITY));
}

export function clampQuantity(q: number, remainingStock: number): number {
  return Math.max(MIN_QUANTITY, Math.min(q, maxQuantity(remainingStock)));
}

export function canIncrease(q: number, remainingStock: number): boolean {
  return q < maxQuantity(remainingStock);
}

export function canDecrease(q: number): boolean {
  return q > MIN_QUANTITY;
}

export function canReserve(q: number, remainingStock: number): boolean {
  return q >= MIN_QUANTITY && q <= maxQuantity(remainingStock);
}
