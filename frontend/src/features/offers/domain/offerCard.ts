import type { Offer } from './offer';

export type OfferCardState = 'onSale' | 'soldOut' | 'ended' | 'scheduled';

export const CARD_STATE_TAG: Record<
  'soldOut' | 'ended' | 'scheduled',
  { text: string; tone: 'mute' | 'none' }
> = {
  soldOut: { text: '품절', tone: 'mute' },
  ended: { text: '판매 종료', tone: 'mute' },
  scheduled: { text: '판매 예정', tone: 'none' },
};

// 서버 우선순위: CLOSED > SUSPENDED > 마감 경과 > SCHEDULED > SOLD_OUT > ON_SALE
export function offerCardState(o: Offer, now: Date): OfferCardState {
  if (o.status === 'CLOSED' || o.status === 'SUSPENDED' || o.salesEnd.getTime() <= now.getTime()) {
    return 'ended';
  }
  if (o.status === 'SCHEDULED') return 'scheduled';
  if (o.status === 'SOLD_OUT' || o.remainingStock === 0) return 'soldOut';
  return 'onSale';
}

export function minutesUntilSalesEnd(o: Offer, now: Date): number {
  return Math.max(0, Math.ceil((o.salesEnd.getTime() - now.getTime()) / 60000));
}

// TODO: 1시간 정각·24시간 이상의 남은 시간과 다른 날 픽업 표기가 임시다.
//   왜: content.md에 해당 경우의 표기가 없다 (docs/design/frontend/offers.md D-15, D-16)
//   언제: 결정 후 (디자인 시스템: content.md 시간 표기 확정)
export function formatSalesEndLabel(minutes: number): string {
  if (minutes < 60) return `판매 마감 ${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest === 0 ? `판매 마감 ${hours}시간 전` : `판매 마감 ${hours}시간 ${rest}분 전`;
}

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

function hm(d: Date): string {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function formatPickupWindow(o: Offer, now: Date): string {
  const head = isSameDay(o.pickupStart, now)
    ? '오늘'
    : `${pad(o.pickupStart.getMonth() + 1)}/${pad(o.pickupStart.getDate())}`;
  return `${head} ${hm(o.pickupStart)}–${hm(o.pickupEnd)}`;
}
