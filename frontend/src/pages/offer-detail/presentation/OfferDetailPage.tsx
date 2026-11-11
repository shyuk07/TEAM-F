import { useCallback } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router';
import { BACK_LABEL, RETRY_LABEL, loginRedirectState, readFrom, useAuth } from '@/features/auth';
import {
  OFFER_DETAIL_LOAD_FAILED_MESSAGE,
  OFFER_NOT_FOUND_MESSAGE,
  OfferDetailBody,
  OfferDetailSkeleton,
  detailReturnPath,
  offerAvailability,
  readQuantityParam,
  unavailableMessage,
  useOfferDetail,
} from '@/features/offers';
import { ReserveOfferPanel } from '@/features/reservations';
import { ROUTES } from '@/shared/lib/routes';
import { useNow } from '@/shared/lib/useNow';

// TODO: 로딩·오류·없음 때 AppBar 제목과 「홈으로」 문구를 임시로 정했다.
//   왜: C2 전용 문구 정본이 없다 (docs/design/frontend/offers.md D-8)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
const FALLBACK_TITLE = '할인 상세';
const GO_HOME_LABEL = '홈으로';

// C2 할인 상세. offers·reservations·auth 부품을 조립한다(docs/design/frontend/offers.md §3.4).
export function OfferDetailPage() {
  const { offerId = '' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const state = useOfferDetail(offerId);
  const auth = useAuth();
  const now = useNow();
  // TODO: ← 는 location.state.from이 없으면 홈으로 간다(history back 안 씀).
  //   왜: 뒤로 가기 대상 정본이 없다 (docs/design/frontend/offers.md D-1)
  //   언제: 결정 후 (사용자: 뒤로 가기 대상)
  const back = readFrom(location.state) ?? ROUTES.home;

  // 패널 useEffect 의존성이라 고정한다.
  const goToCheckout = useCallback((id: string) => void navigate(ROUTES.checkout(id)), [navigate]);

  const detail = state.status === 'success' ? state.detail : null;
  let content;
  if (detail !== null) {
    const availability = offerAvailability(detail.offer, now);
    content = (
      <>
        <OfferDetailBody detail={detail} now={now} />
        <ReserveOfferPanel
          key={detail.offer.id}
          offerId={detail.offer.id}
          unitPrice={detail.offer.salePrice}
          remainingStock={detail.offer.remainingStock}
          reservable={availability.reservable}
          unavailableReason={
            availability.reservable ? null : unavailableMessage(availability.reason)
          }
          // TODO: 세션 확인 중(auth loading)에는 비로그인으로 넘겨, 그 사이 누르면 A1로 간다.
          //   왜: 패널 props에 확인 중 상태가 없다 (docs/design/frontend/offers.md C-4, Q-3)
          //   언제: 결정 후 (사용자: 확인 중 버튼 상태)
          isLoggedIn={auth.state.status === 'authenticated'}
          onRequireLogin={(q) =>
            void navigate(ROUTES.login, {
              state: loginRedirectState(
                'other',
                detailReturnPath(location.pathname, q),
                'reservation',
              ),
            })
          }
          onGoToCheckout={goToCheckout}
          // TODO: 로그인 복귀 후 자동 예약하지 않고 ?qty= 수량만 채운다. 쿼리는 지우지 않는다.
          //   왜: 복귀 후 동작을 임시로 정했다 (docs/design/frontend/offers.md D-5)
          //   언제: 결정 후 (사용자: 자동 예약 여부)
          initialQuantity={readQuantityParam(location.search) ?? undefined}
        />
      </>
    );
  } else if (state.status === 'loading') {
    content = <OfferDetailSkeleton />;
  } else if (state.status === 'notFound') {
    content = (
      <div className="body">
        <div className="warn">{OFFER_NOT_FOUND_MESSAGE}</div>
        <Link className="btn" to={ROUTES.home}>
          {GO_HOME_LABEL}
        </Link>
      </div>
    );
  } else {
    content = (
      <div className="body">
        <div className="warn">{OFFER_DETAIL_LOAD_FAILED_MESSAGE}</div>
        <button type="button" className="btn" onClick={state.retry}>
          {RETRY_LABEL}
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="bar">
        <Link to={back} aria-label={BACK_LABEL}>
          ←
        </Link>
        <h1 className="t">{detail?.offer.productName ?? FALLBACK_TITLE}</h1>
        <span className="sp"></span>
      </div>
      {content}
    </>
  );
}
