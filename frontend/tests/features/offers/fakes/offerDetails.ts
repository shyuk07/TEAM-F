import type { Offer, OfferDetail } from '@/features/offers';
import { at } from '../../../support/clock';
import { makeOffer } from './offers';

export const PICKUP_ADDRESS = '서울시 마포구 망원로 1';
export const NOTICE = '픽업 시 예약 코드를 보여 주세요.';
export const CANCEL_POLICY_TEXT = '취소 시 위약금이 발생할 수 있습니다.';

// 기본값: makeOffer(오늘 18:00 판매 마감, 남은 3개) + 취소 가능 오늘 17:00, 이미지 없음, 설명 없음.
export function makeOfferDetail(
  over: Partial<Omit<OfferDetail, 'offer'>> = {},
  offer: Partial<Offer> = {},
): OfferDetail {
  return {
    offer: makeOffer(offer),
    description: null,
    imageUrls: [],
    pickupAddress: PICKUP_ADDRESS,
    latitude: 37.556,
    longitude: 126.901,
    notice: NOTICE,
    cancellableUntil: at(10, 17, 0),
    cancelPolicyText: CANCEL_POLICY_TEXT,
    ...over,
  };
}
