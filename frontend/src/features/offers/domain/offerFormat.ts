import type { NearbyOffer } from './offer';

export type OfferCardView = {
  storeLine: string;
  title: string;
  rate: string;
  salePrice: string;
  originalPrice: string;
  pickup: string;
  countdown: string | null;
  remaining: string | null;
  soldOut: boolean;
  ended: boolean;
};

export function salesCountdown(salesEnd: Date, now: Date): string | null {
  void salesEnd;
  void now;
  throw new Error('not implemented: salesCountdown');
}

export function pickupWindow(start: Date, end: Date, now: Date): string {
  void start;
  void end;
  void now;
  throw new Error('not implemented: pickupWindow');
}

export function formatDistance(km: number | null): string | null {
  void km;
  throw new Error('not implemented: formatDistance');
}

export function formatWon(n: number): string {
  void n;
  throw new Error('not implemented: formatWon');
}

export function toOfferCardView(item: NearbyOffer, now: Date): OfferCardView {
  void item;
  void now;
  throw new Error('not implemented: toOfferCardView');
}
