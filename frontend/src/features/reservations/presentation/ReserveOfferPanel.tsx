import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { ROUTES } from '@/shared/lib/routes';
import { useReserveOffer } from '../application/useReserveOffer';
import { formatWon } from '../domain/format';
import { reservationTotalPrice } from '../domain/price';
import {
  MY_RESERVATIONS_LINK_LABEL,
  PROCESSING_LABEL,
  RESERVE_CONTINUE_LABEL,
  reserveErrorMessage,
} from '../domain/messages';
import { canDecrease, canIncrease, canReserve, clampQuantity } from '../domain/quantity';

export type ReserveOfferPanelProps = {
  offerId: string;
  unitPrice: number;
  remainingStock: number;
  reservable: boolean;
  unavailableReason: string | null;
  isLoggedIn: boolean;
  onRequireLogin(quantity: number): void;
  onGoToCheckout(reservationId: string): void;
  initialQuantity?: number;
};

// TODO: props는 offers 설계 전 가정이다. offers 상세 응답과 로그인 복귀 시 수량 보존 방식을 맞춘다.
//   왜: offers 설계안이 없어 C2 page와 합의하지 못했다 (docs/design/frontend/reservations.md C-1)
//   언제: C2 구현 시
// TODO: 결제 대기 예약 ID를 찾지 못하면 「결제 이어하기」 대신 내 예약 링크를 보여 준다. 임시 동작이다.
//   왜: 정본이 없다 (docs/design/frontend/reservations.md D-19)
//   언제: 결정 후 (사용자: 중복 예약 ID를 못 찾을 때 이동)
export function ReserveOfferPanel(props: ReserveOfferPanelProps) {
  const { offerId, unitPrice, remainingStock, reservable, unavailableReason, isLoggedIn } = props;
  const { onRequireLogin, onGoToCheckout } = props;
  const [quantity, setQuantity] = useState(() =>
    clampQuantity(props.initialQuantity ?? 1, remainingStock),
  );
  const { submit, pending, error, pendingReservationId, createdReservationId } =
    useReserveOffer(offerId);

  useEffect(() => {
    if (createdReservationId !== null) onGoToCheckout(createdReservationId);
  }, [createdReservationId, onGoToCheckout]);

  const pendingExists = error?.errorCode === 'PENDING_RESERVATION_EXISTS';
  const disabled = pending || !reservable || !canReserve(quantity, remainingStock);

  function reserve() {
    if (disabled) return;
    if (!isLoggedIn) {
      onRequireLogin(quantity);
      return;
    }
    void submit(quantity);
  }

  return (
    <>
      {!reservable && unavailableReason !== null ? (
        <div className="m">{unavailableReason}</div>
      ) : null}
      {error !== null ? (
        <div className="err" role="alert">
          {reserveErrorMessage(error)}
        </div>
      ) : null}
      <div className="cta">
        <div className="step">
          <button
            type="button"
            aria-label="-"
            disabled={!canDecrease(quantity) || pending}
            onClick={() => setQuantity((q) => q - 1)}
          >
            −
          </button>
          <b>{quantity}</b>
          <button
            type="button"
            aria-label="+"
            disabled={!canIncrease(quantity, remainingStock) || pending}
            onClick={() => setQuantity((q) => q + 1)}
          >
            +
          </button>
        </div>
        {pendingExists && pendingReservationId !== null ? (
          <button
            type="button"
            className="btn pri"
            onClick={() => onGoToCheckout(pendingReservationId)}
          >
            {RESERVE_CONTINUE_LABEL}
          </button>
        ) : pendingExists ? (
          <Link className="btn pri" to={ROUTES.reservations}>
            {MY_RESERVATIONS_LINK_LABEL}
          </Link>
        ) : (
          <button type="button" className="btn pri" disabled={disabled} onClick={reserve}>
            {pending
              ? PROCESSING_LABEL
              : `예약하고 결제 ${formatWon(reservationTotalPrice(unitPrice, quantity))}`}
          </button>
        )}
      </div>
    </>
  );
}
