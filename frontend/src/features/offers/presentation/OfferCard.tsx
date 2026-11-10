import { Link, useLocation } from 'react-router';
import { ROUTES } from '@/shared/lib/routes';
import type { NearbyOffer } from '../domain/offer';
import { toOfferCardView } from '../domain/offerFormat';

// 마크업은 wireframe.html:307~318, 정보 순서는 OfferCard README(customer-home.md §3.5).
// TODO: 카드 사진 자리(.ph)에 기본 그림만 둔다.
//   왜: 주변 할인 목록 응답(Offer)에 상품 이미지 필드가 없다 (docs/design/frontend/customer-home.md C-4)
//   언제: 결정 후 (백엔드: Offer 응답에 이미지)
export function OfferCard({ item, now }: { item: NearbyOffer; now: Date }) {
  const location = useLocation();
  const view = toOfferCardView(item, now);
  return (
    // C2 ← 가 필터가 유지된 홈으로 돌아오게 홈 경로 + 쿼리를 넘긴다(customer-home.md §5.4).
    <Link
      className="card"
      to={ROUTES.offerDetail(item.offer.id)}
      state={{ from: location.pathname + location.search }}
    >
      <div className="ph" aria-hidden="true" />
      <div>
        <div className="m">{view.storeLine}</div>
        <div className="t">{view.title}</div>
        <div className="price">
          <span className="pct">{view.rate}</span>
          <b>{view.salePrice}</b>
          <s>{view.originalPrice}</s>
        </div>
        <div className="m">
          {'픽업 '}
          {view.soldOut ? view.pickup : <b>{view.pickup}</b>}
        </div>
        <div className="row">
          {view.soldOut ? (
            <span className="tag mute">품절</span>
          ) : view.ended ? (
            <span className="tag mute">판매 종료</span>
          ) : (
            <>
              <span className="cd">{view.countdown}</span>
              <span className="m">{view.remaining}</span>
            </>
          )}
        </div>
      </div>
    </Link>
  );
}
