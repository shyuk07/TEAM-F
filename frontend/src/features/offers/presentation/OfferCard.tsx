import type { NearbyOffer } from '../domain/offer';
import {
  CARD_STATE_TAG,
  formatPickupWindow,
  formatSalesEndLabel,
  minutesUntilSalesEnd,
  offerCardState,
} from '../domain/offerCard';
import {
  formatDiscountRate,
  formatPlainPrice,
  formatRemaining,
  formatStoreLine,
  formatWon,
} from '../domain/offerFormat';

export type OfferCardProps = { item: NearbyOffer; now: Date };

// TODO: 카드가 이동하지 않는다. 눌러서 C2(할인 상세)로 보낸다.
//   왜: C2 경로·화면이 아직 없다 (docs/design/frontend/offers.md D-18, C-7)
//   언제: C2 구현 시
// TODO: 썸네일이 항상 기본 그림이다.
//   왜: 할인 응답에 이미지 필드가 없다 (docs/design/frontend/offers.md C-3, D-19)
//   언제: 결정 후 (백엔드: 할인 응답에 이미지 필드 추가)
export function OfferCard({ item, now }: OfferCardProps) {
  const { offer, distanceKm } = item;
  const state = offerCardState(offer, now);
  const tag = state === 'onSale' ? null : CARD_STATE_TAG[state];
  return (
    <div className="card">
      <div className="ph" aria-hidden="true" />
      <div>
        <div className="m">{formatStoreLine(offer.storeName, distanceKm)}</div>
        <div className="t">{offer.productName}</div>
        <div className="price">
          <span className="pct">{formatDiscountRate(offer.discountRate)}</span>
          <b>{formatWon(offer.salePrice)}</b>
          <s>{formatPlainPrice(offer.originalPrice)}</s>
        </div>
        <div className="m">
          픽업 <b>{formatPickupWindow(offer, now)}</b>
        </div>
        <div className="row">
          {tag === null ? (
            <>
              <span className="cd">{formatSalesEndLabel(minutesUntilSalesEnd(offer, now))}</span>
              <span className="m">{formatRemaining(offer.remainingStock)}</span>
            </>
          ) : (
            <span className={tag.tone === 'mute' ? 'tag mute' : 'tag'}>{tag.text}</span>
          )}
        </div>
      </div>
    </div>
  );
}
