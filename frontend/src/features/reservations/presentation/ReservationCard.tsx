import { cancelAvailability } from '../domain/cancellation';
import { displayState, statusLabel, statusTone } from '../domain/display';
import {
  formatDate,
  formatQuantity,
  formatTime,
  formatTimeRange,
  formatWon,
} from '../domain/format';
import {
  CANCEL_LINK_LABEL,
  DIRECTIONS_LABEL,
  PICKUP_CODE_LABEL,
  RESERVE_CONTINUE_LABEL,
} from '../domain/messages';
import type { Reservation } from '../domain/reservation';

export type ReservationCardProps = {
  reservation: Reservation;
  now: Date;
  onCancel(reservation: Reservation): void;
  onContinuePayment(reservationId: string): void;
};

// TODO: C5 카드 「길찾기」는 버튼만 두고 동작이 없다. pickupAddress로 열 지도 서비스·URL을 정한다.
//   왜: screens.md C4·C5에 버튼만 있고 지도 링크 정본이 없다 (docs/design/frontend/reservations.md D-18)
//   언제: 결정 후 (사용자: 지도 서비스)
export function ReservationCard({
  reservation: r,
  now,
  onCancel,
  onContinuePayment,
}: ReservationCardProps) {
  const state = displayState(r, now);
  const tag = (
    <span className={`tag ${statusTone(state)}`}>
      {statusLabel(state)}
      {state === 'CANCELLED_BY_CUSTOMER' ? <span className="m"> 직접 취소</span> : null}
    </span>
  );

  // 진행 중 상태만 행동을 그린다. 미수령·완료·취소는 지난 예약 카드 모양.
  const live = state === 'PENDING_PAYMENT' || state === 'RESERVED';
  if (!live && state !== 'CANCELLED_BY_STORE') {
    return (
      <div className="box">
        <div className="row">
          {tag}
          <span className="sp"></span>
          <span className="m">{formatDate(r.createdAt)}</span>
        </div>
        <div className="t">{formatQuantity(r.productName, r.quantity)}</div>
        <div className="m">{formatWon(r.totalPrice)}</div>
      </div>
    );
  }

  const cancel = cancelAvailability(r, now);
  return (
    <div className="box">
      <div className="row">{tag}</div>
      <div className="t">{formatQuantity(r.productName, r.quantity)}</div>
      <div className="m">{`${r.storeName} · ${formatTimeRange(r.pickupStart, r.pickupEnd)}`}</div>
      {state === 'RESERVED' ? (
        <div className="codebox">
          <div className="lbl">{PICKUP_CODE_LABEL}</div>
          <div className="code">{r.pickupCode}</div>
          <div className="m">
            <b>{`${formatTime(r.createdAt)} 예약`}</b>
          </div>
        </div>
      ) : null}
      {live ? (
        <div className="row">
          {state === 'RESERVED' ? (
            <button type="button" className="btn sm">
              {DIRECTIONS_LABEL}
            </button>
          ) : (
            <button type="button" className="btn sm pri" onClick={() => onContinuePayment(r.id)}>
              {RESERVE_CONTINUE_LABEL}
            </button>
          )}
          <span className="sp"></span>
          {cancel.kind === 'cancellable' ? (
            <button type="button" className="link" onClick={() => onCancel(r)}>
              {cancel.until === null
                ? CANCEL_LINK_LABEL
                : `${CANCEL_LINK_LABEL} · ${formatTime(cancel.until)}까지`}
            </button>
          ) : null}
          {cancel.kind === 'deadlinePassed' ? (
            <span className="m">{`취소 마감 지남 (${formatTime(cancel.until)})`}</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
