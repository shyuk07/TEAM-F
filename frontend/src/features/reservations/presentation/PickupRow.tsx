import { formatHm, groupDigits } from '@/shared/lib/format';
import { rowTitle } from '../domain/reservationFormat';
import type { StoreReservation } from '../domain/storeReservation';

// TODO: 「픽업 시간」 열이 없다
//   왜: 목록 응답에 pickup_start·pickup_end가 없다 (owner-today.md B-1)
//   언제: 결정 후 (백엔드: 목록에 픽업 시간 추가)
export type PickupRowProps = {
  reservation: StoreReservation;
  isSelected?: boolean;
  onClick?: () => void;
};

export function PickupRow({ reservation, isSelected, onClick }: PickupRowProps) {
  const title = rowTitle(reservation);
  const amountStr = `${groupDigits(reservation.totalPrice)}원`;
  const reservedTime = formatHm(reservation.createdAt);

  return (
    <div
      className={`tr ${isSelected ? 'sel' : ''}`}
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-selected={isSelected}
    >
      <div>
        <b>{title}</b>
        <div className="m mob">
          픽업 — · {amountStr} · {reservedTime} 예약
        </div>
      </div>
      <span className="hide">—</span>
      <span className="hide">{amountStr}</span>
      <span className="hide">{reservedTime}</span>
      <span />
    </div>
  );
}
