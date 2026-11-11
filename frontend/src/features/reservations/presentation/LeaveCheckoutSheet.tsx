import { useId } from 'react';
import { ReservationModal } from './ReservationModal';
import { useCancelReservation } from '../application/useCancelReservation';
import {
  LEAVE_CANCEL_LABEL,
  LEAVE_CONTINUE_LABEL,
  LEAVE_PAY_LATER_LABEL,
  LEAVE_SHEET_TITLE,
  PROCESSING_LABEL,
  cancelErrorMessage,
} from '../domain/messages';

export type LeaveCheckoutSheetProps = {
  reservationId: string;
  onContinue(): void;
  onCancelled(): void;
  onPayLater(): void;
  /** 결제 처리 중 등 바깥 사정으로 취소를 막을 때 true. */
  cancelDisabled?: boolean;
};

export function LeaveCheckoutSheet({
  reservationId,
  onContinue,
  onCancelled,
  onPayLater,
  cancelDisabled = false,
}: LeaveCheckoutSheetProps) {
  const titleId = useId();
  const { cancel, pending, error } = useCancelReservation();

  async function cancelAndLeave() {
    if (cancelDisabled) return;
    if (await cancel(reservationId)) onCancelled();
  }

  return (
    <ReservationModal
      labelledBy={titleId}
      onDismiss={() => {
        if (!pending) onContinue();
      }}
    >
      <div className="t" id={titleId}>
        {LEAVE_SHEET_TITLE}
      </div>
      {error !== null ? (
        <div className="err" role="alert">
          {cancelErrorMessage(error)}
        </div>
      ) : null}
      <button type="button" className="btn dark" disabled={pending} onClick={onContinue}>
        {LEAVE_CONTINUE_LABEL}
      </button>
      <button
        type="button"
        className="btn"
        disabled={pending || cancelDisabled}
        onClick={() => void cancelAndLeave()}
      >
        {pending ? PROCESSING_LABEL : LEAVE_CANCEL_LABEL}
      </button>
      <button type="button" className="link" disabled={pending} onClick={onPayLater}>
        {LEAVE_PAY_LATER_LABEL}
      </button>
    </ReservationModal>
  );
}
