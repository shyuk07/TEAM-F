import { useId } from 'react';
import { useCancelReservation } from '../application/useCancelReservation';
import { formatQuantity } from '../domain/format';
import { shouldRefreshAfterCancelError } from '../domain/cancellation';
import { ReservationModal } from './ReservationModal';
import {
  CANCEL_SHEET_BACK_LABEL,
  CANCEL_SHEET_CONFIRM_LABEL,
  CANCEL_SHEET_TITLE,
  PENDING_REFUND_NOTICE,
  PROCESSING_LABEL,
  REFUND_NOTICE,
  cancelErrorMessage,
} from '../domain/messages';
import type { Reservation } from '../domain/reservation';

export type CancelReservationSheetProps = {
  reservation: Reservation;
  onClose(): void;
  onCancelled(): void;
  onRefresh?(): void;
};

export function CancelReservationSheet({
  reservation: r,
  onClose,
  onCancelled,
  onRefresh,
}: CancelReservationSheetProps) {
  const titleId = useId();
  const { cancel, pending, error } = useCancelReservation();

  async function confirm() {
    if (
      await cancel(r.id, (failure) => {
        if (shouldRefreshAfterCancelError(failure)) onRefresh?.();
      })
    )
      onCancelled();
  }

  return (
    <ReservationModal
      labelledBy={titleId}
      onDismiss={() => {
        if (!pending) onClose();
      }}
    >
      <div className="t" id={titleId}>
        {CANCEL_SHEET_TITLE}
      </div>
      <div className="box">
        <div className="kv">
          <span>상품</span>
          <span>{formatQuantity(r.productName, r.quantity)}</span>
        </div>
        {r.status === 'PENDING_PAYMENT' ? (
          <div className="m">{PENDING_REFUND_NOTICE}</div>
        ) : (
          <div className="m">{REFUND_NOTICE}</div>
        )}
      </div>
      {error !== null ? (
        <div className="err" role="alert">
          {cancelErrorMessage(error)}
        </div>
      ) : null}
      <button type="button" className="btn" disabled={pending} onClick={onClose}>
        {CANCEL_SHEET_BACK_LABEL}
      </button>
      <button type="button" className="btn dark" disabled={pending} onClick={() => void confirm()}>
        {pending ? PROCESSING_LABEL : CANCEL_SHEET_CONFIRM_LABEL}
      </button>
    </ReservationModal>
  );
}
