import type { Offer } from './offer';
import { formatHm, formatWon, salesCountdown } from './offerFormat';

export const OWNER_FILTERS = [
  { key: 'ON_SALE', label: '판매 중' },
  { key: 'SCHEDULED', label: '판매 예정' },
  { key: 'SOLD_OUT', label: '품절' },
  { key: 'CLOSED', label: '판매 종료' },
] as const;

export type OwnerFilter = (typeof OWNER_FILTERS)[number]['key'];

export type OwnerRowAction = 'edit' | 'adjust' | 'deactivate' | 'relist';

export function ownerStatusTag(offer: Offer): { label: string; tone?: 'ok' | 'mute' | 'hot' } {
  switch (offer.status) {
    case 'ON_SALE':
      return { label: '판매 중', tone: 'ok' };
    case 'SCHEDULED':
      return { label: '판매 예정' };
    case 'SOLD_OUT':
      return { label: '품절', tone: 'mute' };
    case 'CLOSED':
      return { label: '판매 종료', tone: 'mute' };
    case 'SUSPENDED':
      return { label: '판매 종료', tone: 'hot' };
    default:
      return { label: '판매 종료', tone: 'mute' };
  }
}

export function ownerRowActions(offer: Offer, now: Date): OwnerRowAction[] {
  void now;
  if (offer.status === 'SUSPENDED') {
    return [];
  }
  if (
    offer.isActive &&
    (offer.status === 'ON_SALE' || offer.status === 'SCHEDULED' || offer.status === 'SOLD_OUT')
  ) {
    return ['edit', 'adjust', 'deactivate'];
  }
  if (offer.status === 'CLOSED') {
    return ['relist'];
  }
  return [];
}

export function countByFilter(offers: Offer[]): {
  onSale: number;
  scheduled: number;
  soldOut: number;
} {
  let onSale = 0;
  let scheduled = 0;
  let soldOut = 0;
  for (const o of offers) {
    if (o.status === 'ON_SALE') onSale++;
    else if (o.status === 'SCHEDULED') scheduled++;
    else if (o.status === 'SOLD_OUT') soldOut++;
  }
  return { onSale, scheduled, soldOut };
}

export function matchesFilter(offer: Offer, filter: OwnerFilter): boolean {
  if (filter === 'CLOSED') {
    return offer.status === 'CLOSED' || offer.status === 'SUSPENDED';
  }
  return offer.status === filter;
}

export function ownerRowSummary(
  offer: Offer,
  now: Date,
): {
  title: string;
  meta: string;
  countdown: string | null;
} {
  const title = `${offer.productName} · ${formatWon(offer.salePrice)} (${offer.discountRate}%)`;
  const meta = `남은 ${offer.remainingStock} / ${offer.initialStock} · 픽업 ${formatHm(offer.pickupStart)}–${formatHm(offer.pickupEnd)}`;
  const countdown = offer.status === 'ON_SALE' ? salesCountdown(offer.salesEnd, now) : null;
  return { title, meta, countdown };
}
