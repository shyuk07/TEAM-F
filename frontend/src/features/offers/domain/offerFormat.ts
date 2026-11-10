import { formatHm, formatMd, groupDigits, isSameLocalDate } from '@/shared/lib/format';
import { isSoldOut, type NearbyOffer } from './offer';

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

const MINUTE_MS = 60_000;

// 「판매 마감 N분 전 / N시간 N분 전」(content.md, states.md 화면 계산 값). 마감 시각이 지나면 null.
// TODO: 카운트다운 경계 표기(1분 미만 올림, 정각 「N시간 전」, 24시간 이상도 시간)를 임시로 정했다.
//   왜: content.md에 경계 표기 정본이 없다 (docs/design/frontend/customer-home.md D-13, Q-9)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export function salesCountdown(salesEnd: Date, now: Date): string | null {
  const diff = salesEnd.getTime() - now.getTime();
  if (diff <= 0) return null;
  const m = Math.ceil(diff / MINUTE_MS);
  if (m < 60) return `판매 마감 ${m}분 전`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r === 0 ? `판매 마감 ${h}시간 전` : `판매 마감 ${h}시간 ${r}분 전`;
}

function pickupDay(start: Date, now: Date): string {
  if (isSameLocalDate(start, now)) return '오늘';
  const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  if (isSameLocalDate(start, tomorrow)) return '내일';
  return formatMd(start);
}

// 「오늘 18:00–20:00」(en dash U+2013, content.md). 화면이 앞에 「픽업 」을 붙인다.
export function pickupWindow(start: Date, end: Date, now: Date): string {
  return `${pickupDay(start, now)} ${formatHm(start)}–${formatHm(end)}`;
}

// 소수 1자리, 최소 0.1km. 위치가 없으면 null(거리 숨김).
// TODO: 0.05km 미만 거리를 0.1km로 올려 보인다.
//   왜: content.md에 아주 가까운 거리 표기 정본이 없다 (docs/design/frontend/customer-home.md D-13, Q-10)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export function formatDistance(km: number | null): string | null {
  if (km === null) return null;
  const v = Math.max(Math.round(km * 10) / 10, 0.1);
  return `${v.toFixed(1)}km`;
}

export function formatWon(n: number): string {
  return `${groupDigits(n)}원`;
}

// 카드 정보 순서는 OfferCard README를 따른다(customer-home.md §3.1).
export function toOfferCardView(item: NearbyOffer, now: Date): OfferCardView {
  const { offer } = item;
  const distance = formatDistance(item.distanceKm);
  const soldOut = isSoldOut(offer);
  const countdown = soldOut ? null : salesCountdown(offer.salesEnd, now);
  return {
    storeLine: distance !== null ? `${offer.storeName} · ${distance}` : offer.storeName,
    title: offer.productName,
    rate: `${offer.discountRate}%`,
    salePrice: formatWon(offer.salePrice),
    originalPrice: groupDigits(offer.originalPrice),
    pickup: pickupWindow(offer.pickupStart, offer.pickupEnd, now),
    countdown,
    remaining: soldOut ? null : `남은 ${offer.remainingStock}개`,
    soldOut,
    ended: !soldOut && countdown === null,
  };
}
