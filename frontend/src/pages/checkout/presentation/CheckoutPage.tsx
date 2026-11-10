import { useCallback, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { useAuth } from '@/features/auth';
import { PaymentForm } from '@/features/payments';
import {
  LeaveCheckoutSheet,
  MY_RESERVATIONS_LINK_LABEL,
  isPayable,
  useMyReservation,
} from '@/features/reservations';
import { ROUTES } from '@/shared/lib/routes';

// TODO: 예약을 못 찾았을 때·결제할 수 없는 예약일 때·불러오기 실패 기본 문구는 임시다.
//   왜: screens.md C3에 해당 문구가 없다 (docs/design/frontend/payments.md D-6)
//   언제: 결정 후 (디자인 시스템: C3 안내 문구)
const NOT_FOUND_MESSAGE = '예약을 찾을 수 없어요.';
const NOT_PAYABLE_MESSAGE = '결제할 수 있는 예약이 아니에요.';
const LOAD_FALLBACK_MESSAGE = '불러오지 못했어요. 잠시 후 다시 시도해 주세요.';

// TODO: C3a에서 예약을 취소하면 홈으로 보낸다. 설계안은 C2(할인 상세)로 보내는 안이다.
//   왜: C2 경로가 아직 없다 (docs/design/frontend/reservations.md D-20)
//   언제: C2 구현 시
export function CheckoutPage() {
  const { reservationId = '' } = useParams();
  const navigate = useNavigate();
  const { state: auth } = useAuth();
  const reservation = useMyReservation(reservationId);
  const [leaving, setLeaving] = useState(false);
  const [paying, setPaying] = useState(false);
  const onPendingChange = useCallback((p: boolean) => setPaying(p), []);
  const payable = reservation.status === 'success' && isPayable(reservation.reservation);

  // 결제 대기 예약을 읽었을 때만 C3a를 띄운다. 그 밖에는 그냥 뒤로 간다. 결제 처리 중에는 막는다.
  function goBack() {
    if (paying) return;
    if (payable) setLeaving(true);
    else void navigate(-1);
  }
  const pointBalance = auth.status === 'authenticated' ? auth.user.point : 0;

  let body;
  if (reservation.status === 'loading') {
    body = (
      <div className="body" aria-busy="true">
        <div className="card">
          <div className="sk"></div>
          <div className="sk"></div>
        </div>
      </div>
    );
  } else if (!payable || reservation.status !== 'success') {
    const message =
      reservation.status === 'notFound'
        ? NOT_FOUND_MESSAGE
        : reservation.status === 'error'
          ? reservation.message || LOAD_FALLBACK_MESSAGE
          : NOT_PAYABLE_MESSAGE;
    body = (
      <div className="body">
        <div className="warn">{message}</div>
        <Link className="btn" to={ROUTES.myReservations}>
          {MY_RESERVATIONS_LINK_LABEL}
        </Link>
      </div>
    );
  } else {
    const r = reservation.reservation;
    body = (
      <PaymentForm
        reservationId={r.id}
        productName={r.productName}
        quantity={r.quantity}
        totalPrice={r.totalPrice}
        pointBalance={pointBalance}
        onPaid={() => void navigate(ROUTES.paymentComplete(r.id), { replace: true })}
        onPendingChange={onPendingChange}
      />
    );
  }

  return (
    <>
      <div className="bar">
        <button type="button" aria-label="뒤로" disabled={paying} onClick={goBack}>
          ←
        </button>
        <span className="t">결제</span>
        <span className="sp"></span>
      </div>
      {body}
      {leaving ? (
        <LeaveCheckoutSheet
          reservationId={reservationId}
          cancelDisabled={paying}
          onContinue={() => setLeaving(false)}
          onCancelled={() => void navigate(ROUTES.home, { replace: true })}
          onPayLater={() => void navigate(ROUTES.myReservations, { replace: true })}
        />
      ) : null}
    </>
  );
}
