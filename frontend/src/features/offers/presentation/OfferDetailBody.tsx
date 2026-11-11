import { groupDigits } from '@/shared/lib/format';
import { offerAvailability } from '../domain/offerAvailability';
import type { OfferDetail } from '../domain/offerDetail';
import { cancelDeadlineText, formatWon, pickupWindow, salesCountdown } from '../domain/offerFormat';
import {
  CANCEL_DEADLINE_LABEL,
  MAX_PER_RESERVATION_TEXT,
  PICKUP_TIME_LABEL,
} from '../domain/offerMessages';
import { OfferImage } from './OfferImage';

// .body 안 내용(wireframe.html 350~357줄). 예약 패널은 page가 이어 붙인다.
// 판매 불가면 카운트다운·남은 수량을 숨긴다. 사유 문구는 예약 패널 한 곳에만 보인다.
// TODO: 안내는 서버 notice를 그대로, 취소는 content.md 문구로 보이고 서버 cancel_policy.description은 숨긴다.
//   왜: 서버 notice와 와이어프레임 문구가 다르고 취소 정책 서버 문구가 디자인과 다르다 (docs/design/frontend/offers.md C-2, D-7)
//   언제: 결정 후 (사용자: 안내·취소 문구 정본)
export function OfferDetailBody({ detail, now }: { detail: OfferDetail; now: Date }) {
  const { offer } = detail;
  const availability = offerAvailability(offer, now);
  const countdown = salesCountdown(offer.salesEnd, now);
  return (
    <div className="body">
      <OfferImage urls={detail.imageUrls} alt={offer.productName} />
      <div className="m">{`${offer.storeName} · ${detail.pickupAddress}`}</div>
      <div className="price">
        <span className="pct">{offer.discountRate}%</span>
        <b>{formatWon(offer.salePrice)}</b>
        <s>{groupDigits(offer.originalPrice)}</s>
      </div>
      <div className="row">
        {availability.reservable ? (
          <>
            {countdown !== null ? <span className="cd">{countdown}</span> : null}
            <span className="m">{`남은 ${offer.remainingStock}개`}</span>
          </>
        ) : null}
      </div>
      <div className="box">
        <div className="kv">
          <span>{PICKUP_TIME_LABEL}</span>
          <b>{pickupWindow(offer.pickupStart, offer.pickupEnd, now)}</b>
        </div>
        <div className="kv">
          <span>{CANCEL_DEADLINE_LABEL}</span>
          <b>{cancelDeadlineText(detail.cancellableUntil, now)}</b>
        </div>
      </div>
      {detail.description !== null ? <div className="m">{detail.description}</div> : null}
      <div className="m">{detail.notice}</div>
      <div className="m">{MAX_PER_RESERVATION_TEXT}</div>
    </div>
  );
}
