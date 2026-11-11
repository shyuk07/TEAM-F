import { isSoldOut, type Offer } from './offer';

export type UnavailableReason = 'soldOut' | 'ended' | 'notStarted' | 'inactive';

export type OfferAvailability =
  { reservable: true } | { reservable: false; reason: UnavailableReason };

// 판정 순서: 품절 → 종료 → 비활성 → 판매 전 → 가능 (offers.md §3.2)
export function offerAvailability(offer: Offer, now: Date): OfferAvailability {
  if (isSoldOut(offer)) return { reservable: false, reason: 'soldOut' };
  // 마감 정각(salesEnd == now)은 종료로 본다(salesCountdown의 diff <= 0과 맞춤). SUSPENDED는 방어.
  if (offer.status === 'CLOSED' || offer.status === 'SUSPENDED' || offer.salesEnd <= now) {
    return { reservable: false, reason: 'ended' };
  }
  if (!offer.isActive) return { reservable: false, reason: 'inactive' };
  if (offer.status === 'SCHEDULED' || offer.salesStart > now) {
    return { reservable: false, reason: 'notStarted' };
  }
  return { reservable: true };
}

// TODO: 판매 불가 사유 문구 4종을 임시로 정했다.
//   왜: 사유 문구 정본이 없다 (docs/design/frontend/offers.md D-6)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
const UNAVAILABLE_MESSAGES: Record<UnavailableReason, string> = {
  soldOut: '품절됐어요.',
  ended: '판매가 종료됐어요.',
  inactive: '지금은 판매하지 않는 상품이에요.',
  notStarted: '아직 판매 전이에요.',
};

export function unavailableMessage(reason: UnavailableReason): string {
  return UNAVAILABLE_MESSAGES[reason];
}
