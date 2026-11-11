import { useState } from 'react';
import { Link, useLocation } from 'react-router';
import { ROUTES } from '@/shared/lib/routes';
import type { NearbyOffer } from '../domain/offer';
import { toOfferCardView } from '../domain/offerFormat';

// 마크업은 wireframe.html:307~318, 정보 순서는 OfferCard README(customer-home.md §3.5).
// 사진 자리(.ph)는 첫 이미지를 채우고, 없거나 로드에 실패하면 기본 그림을 둔다.
// .ph 규칙은 div용이라 img가 원본 크기로 넘친다. 썸네일 칸(--thumb)에 맞춰 자르고 채운다.
const THUMB_IMAGE_STYLE = {
  display: 'block',
  width: '100%',
  maxWidth: 'var(--thumb)',
  height: 'var(--thumb)',
  minWidth: 0,
  objectFit: 'cover',
} as const;

export function OfferCard({ item, now }: { item: NearbyOffer; now: Date }) {
  const location = useLocation();
  const view = toOfferCardView(item, now);
  const src = item.imageUrls[0];
  // 실패한 주소를 기억한다. 주소가 바뀌면 다시 시도한다.
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  return (
    // C2 ← 가 필터가 유지된 홈으로 돌아오게 홈 경로 + 쿼리를 넘긴다(customer-home.md §5.4).
    <Link
      className="card"
      to={ROUTES.offerDetail(item.offer.id)}
      state={{ from: location.pathname + location.search }}
    >
      {src === undefined || failedSrc === src ? (
        <div className="ph" aria-hidden="true" />
      ) : (
        <img
          className="ph"
          src={src}
          alt=""
          loading="lazy"
          style={THUMB_IMAGE_STYLE}
          onError={() => setFailedSrc(src)}
        />
      )}
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
