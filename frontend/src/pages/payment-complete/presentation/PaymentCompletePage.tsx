import { Link, useParams } from 'react-router';
import {
  DIRECTIONS_LABEL,
  MY_RESERVATIONS_LINK_LABEL,
  displayState,
  formatDate,
  formatTime,
  isSameKstDate,
  formatTimeRange,
  statusLabel,
  statusTone,
  useMyReservation,
} from '@/features/reservations';
import { ROUTES } from '@/shared/lib/routes';

// TODO: 예약을 못 찾았을 때·불러오기 실패 기본 문구는 임시다.
//   왜: screens.md C4에 해당 문구가 없다 (docs/design/frontend/payments.md §2.6)
//   언제: 결정 후 (디자인 시스템: C4 안내 문구)
const NOT_FOUND_MESSAGE = '예약을 찾을 수 없어요.';
const LOAD_FALLBACK_MESSAGE = '불러오지 못했어요. 잠시 후 다시 시도해 주세요.';
const CODE_LABEL = '매장에서 이 코드를 보여 주세요';

// TODO: 결제 뒤 보유 포인트를 다시 불러오지 않는다(useAuth().reload()).
//   왜: reload가 세션 상태를 loading으로 바꾸면 CustomerLayout이 이 화면을 다시 마운트해 반복될 수 있다 (docs/design/frontend/payments.md D-9)
//   언제: 결정 후 (사용자: 결제 후 포인트 갱신 방식)
// TODO: 「길찾기」는 버튼만 두고 동작이 없다.
//   왜: 지도 링크 정본이 없다 (docs/design/frontend/reservations.md D-18)
//   언제: 결정 후 (사용자: 지도 서비스)
export function PaymentCompletePage() {
  const { reservationId = '' } = useParams();
  const state = useMyReservation(reservationId);

  const bar = (
    <div className="bar">
      <span className="t">결제 완료</span>
      <span className="sp"></span>
    </div>
  );
  const myLink = (
    <Link className="btn" to={ROUTES.myReservations}>
      {MY_RESERVATIONS_LINK_LABEL}
    </Link>
  );

  if (state.status === 'loading') {
    return (
      <>
        {bar}
        <div className="body" aria-busy="true">
          <div className="card">
            <div className="sk"></div>
            <div className="sk"></div>
          </div>
        </div>
      </>
    );
  }
  if (state.status !== 'success') {
    return (
      <>
        {bar}
        <div className="body">
          <div className="warn">
            {state.status === 'notFound'
              ? NOT_FOUND_MESSAGE
              : state.message || LOAD_FALLBACK_MESSAGE}
          </div>
          {myLink}
        </div>
      </>
    );
  }

  const r = state.reservation;
  const now = new Date();
  const display = displayState(r, now);
  return (
    <>
      {bar}
      <div className="body">
        <span className={`tag ${statusTone(display)}`}>{statusLabel(display)}</span>
        <div className="box codebox">
          <div className="lbl">{CODE_LABEL}</div>
          <div className="code">{r.pickupCode}</div>
        </div>
        <div className="box">
          <div className="kv">
            <span>픽업</span>
            <span>{formatTimeRange(r.pickupStart, r.pickupEnd)}</span>
          </div>
          <div className="kv">
            <span>매장</span>
            <span>{`${r.storeName} · ${r.pickupAddress}`}</span>
          </div>
          <div className="kv">
            <span>취소 가능</span>
            <span>
              {isSameKstDate(r.cancellableUntil, now)
                ? `오늘 ${formatTime(r.cancellableUntil)}까지`
                : `${formatDate(r.cancellableUntil)} ${formatTime(r.cancellableUntil)}까지`}
            </span>
          </div>
        </div>
      </div>
      <div className="cta">
        <button type="button" className="btn">
          {DIRECTIONS_LABEL}
        </button>
        {myLink}
      </div>
    </>
  );
}
