import { useState, type FormEvent } from 'react';
import { Button } from '@/shared/ui/Button';
import { FieldError } from '@/shared/ui/FieldError';
import { Input } from '@/shared/ui/Input';
import { validateDeactivate } from '../domain/deactivation';
import type { Offer } from '../domain/offer';
import { formatWon } from '../domain/offerFormat';

export type OfferDeactivateFormProps = {
  offer: Offer;
  isPending?: boolean;
  errorMessage?: string | null;
  formId?: string;
  onCancel: () => void;
  onSubmit: (reason: string, cancelReservations: boolean) => Promise<void>;
};

export function OfferDeactivateForm({
  offer,
  isPending,
  errorMessage: serverError,
  formId = 'offer-deactivate-form',
  onCancel,
  onSubmit,
}: OfferDeactivateFormProps) {
  const [reason, setReason] = useState<string>('');
  const [cancelReservations, setCancelReservations] = useState<boolean>(false);

  const issue = validateDeactivate({ reason });
  let clientError: string | null = null;
  if (reason.trim() !== '' && issue === 'reason-too-long') {
    clientError = '중단 사유는 200자 이내로 입력해 주세요.';
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (issue !== null || isPending) return;
    await onSubmit(reason, cancelReservations);
  };

  const displayError = clientError ?? serverError;

  return (
    <form id={formId} onSubmit={handleSubmit} className="grid" style={{ maxWidth: 480 }}>
      <div className="box">
        <div className="t">
          {offer.productName} · {formatWon(offer.salePrice)}
        </div>
        <div className="m">
          지금 남은 {offer.remainingStock}개 / 최초 {offer.initialStock}개
        </div>
      </div>

      <Input
        label="중단 사유 *"
        value={reason}
        maxLength={200}
        readOnly={isPending}
        onChange={setReason}
      />

      <div className="lbl">기존 예약은?</div>
      <div
        className="box"
        role="radio"
        aria-checked={!cancelReservations}
        tabIndex={0}
        style={{
          cursor: isPending ? 'default' : 'pointer',
          outline: !cancelReservations ? '2px solid var(--fg)' : 'none',
          outlineOffset: -2,
        }}
        onClick={() => !isPending && setCancelReservations(false)}
        onKeyDown={(e) => {
          if (!isPending && (e.key === ' ' || e.key === 'Enter')) {
            setCancelReservations(false);
          }
        }}
      >
        <b>{!cancelReservations ? '●' : '○'} 그대로 두기</b>
        <div className="m">새 예약만 막고, 예약한 고객은 픽업 가능</div>
      </div>

      <div
        className="box"
        role="radio"
        aria-checked={cancelReservations}
        tabIndex={0}
        style={{
          cursor: isPending ? 'default' : 'pointer',
          outline: cancelReservations ? '2px solid var(--fg)' : 'none',
          outlineOffset: -2,
        }}
        onClick={() => !isPending && setCancelReservations(true)}
        onKeyDown={(e) => {
          if (!isPending && (e.key === ' ' || e.key === 'Enter')) {
            setCancelReservations(true);
          }
        }}
      >
        <b>{cancelReservations ? '●' : '○'} 모두 취소하고 전액 환불</b>
        <div className="m">
          고객 앱의 예약에 "매장 사정으로 취소됨 · 전액 환불"로 표시돼요. 문자·알림은 가지 않아요.
        </div>
      </div>

      {displayError ? <FieldError>{displayError}</FieldError> : null}

      <div className="row dk" style={{ marginTop: 'var(--s3)' }}>
        <Button onClick={onCancel} disabled={isPending}>
          취소
        </Button>
        <span className="sp" />
        <Button type="submit" variant="dark" pending={isPending} disabled={issue !== null}>
          판매 중단
        </Button>
      </div>
    </form>
  );
}
