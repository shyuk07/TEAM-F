import type { NewOffer } from './offerCommands';

export type SalesStart = 'now' | Date;

export type OfferDraft = {
  productId: string;
  salePrice: number;
  initialStock: number;
  salesStart: SalesStart;
  salesEnd: Date;
  pickupStart: Date;
  pickupEnd: Date;
  quickPick: number | 'custom';
};

export const QUICK_PICKS = [30, 60, 120, 180] as const;

export function quickPickLabel(minutes: number): string {
  switch (minutes) {
    case 30:
      return '30분 후 · 취소 불가';
    case 60:
      return '1시간 후 · 취소 불가';
    case 120:
      return '2시간 후';
    case 180:
      return '3시간 후';
    default:
      return `${minutes}분 후`;
  }
}

export function defaultDraft(now: Date, base?: Partial<OfferDraft>): OfferDraft {
  const pickupStart = new Date(now.getTime() + 120 * 60 * 1000);
  const salesEnd = new Date(pickupStart.getTime());
  const pickupEnd = new Date(pickupStart.getTime() + 120 * 60 * 1000);

  return {
    productId: base?.productId ?? '',
    salePrice: base?.salePrice ?? 0,
    initialStock: base?.initialStock ?? 10,
    salesStart: 'now',
    salesEnd,
    pickupStart,
    pickupEnd,
    quickPick: 120,
    ...base,
  };
}

export function applyQuickPick(draft: OfferDraft, minutes: number, now: Date): OfferDraft {
  const pickupStart = new Date(now.getTime() + minutes * 60 * 1000);
  const salesEnd = new Date(pickupStart.getTime());
  const pickupEnd = new Date(pickupStart.getTime() + 120 * 60 * 1000);

  return {
    ...draft,
    pickupStart,
    salesEnd,
    pickupEnd,
    salesStart: 'now',
    quickPick: minutes,
  };
}

export function pickupLeadMinutes(draft: OfferDraft, now: Date): number {
  return Math.floor((draft.pickupStart.getTime() - now.getTime()) / 60000);
}

export function cancelDeadline(draft: OfferDraft): Date {
  return new Date(draft.pickupStart.getTime() - 60 * 60 * 1000);
}

export function isCancelBlocked(draft: OfferDraft, now: Date): boolean {
  return pickupLeadMinutes(draft, now) <= 60;
}

export type DraftIssue =
  | 'price-not-integer'
  | 'price-zero-or-less'
  | 'price-gte-original'
  | 'stock-not-integer'
  | 'stock-zero-or-less'
  | 'stock-over-max'
  | 'sales-end-before-start'
  | 'pickup-end-before-sales-end'
  | 'pickup-end-before-pickup-start';

export function validateDraft(draft: OfferDraft, originalPrice: number, now: Date): DraftIssue[] {
  const issues: DraftIssue[] = [];

  if (!Number.isInteger(draft.salePrice)) {
    issues.push('price-not-integer');
  }
  if (draft.salePrice <= 0) {
    issues.push('price-zero-or-less');
  }
  if (originalPrice > 0 && draft.salePrice >= originalPrice) {
    issues.push('price-gte-original');
  }

  if (!Number.isInteger(draft.initialStock)) {
    issues.push('stock-not-integer');
  }
  if (draft.initialStock < 1) {
    issues.push('stock-zero-or-less');
  }
  if (draft.initialStock > 9999) {
    issues.push('stock-over-max');
  }

  const effectiveSalesStart = draft.salesStart === 'now' ? now : draft.salesStart;
  if (draft.salesEnd.getTime() <= effectiveSalesStart.getTime()) {
    issues.push('sales-end-before-start');
  }
  if (draft.pickupEnd.getTime() <= draft.salesEnd.getTime()) {
    issues.push('pickup-end-before-sales-end');
  }
  if (draft.pickupEnd.getTime() <= draft.pickupStart.getTime()) {
    issues.push('pickup-end-before-pickup-start');
  }

  return issues;
}

export function toCreateInput(draft: OfferDraft): NewOffer {
  return {
    salePrice: draft.salePrice,
    initialStock: draft.initialStock,
    salesStart: draft.salesStart === 'now' ? undefined : draft.salesStart,
    salesEnd: draft.salesEnd,
    pickupStart: draft.pickupStart,
    pickupEnd: draft.pickupEnd,
  };
}
