import { useState, type FormEvent } from 'react';
import { Button } from '@/shared/ui/Button';
import { FieldError } from '@/shared/ui/FieldError';
import { Input } from '@/shared/ui/Input';
import { Stepper } from '@/shared/ui/Stepper';
import type { Offer } from '../domain/offer';
import { formatWon } from '../domain/offerFormat';
import {
  diffOfferChanges,
  hasChanges,
  quantityFloor,
  type OfferEditValues,
} from '../domain/offerEdit';
import { OWNER_OFFER_MESSAGES } from '../domain/ownerOfferMessages';
import { OfferScheduleFields } from './OfferScheduleFields';

export type OfferEditFormProps = {
  offer: Offer;
  now: Date;
  isPending?: boolean;
  isLocked?: boolean;
  errorMessage?: string | null;
  formId?: string;
  onDeactivateClick?: () => void;
  onSubmit: (values: OfferEditValues) => Promise<void>;
};

export function OfferEditForm({
  offer,
  now,
  isPending,
  isLocked,
  errorMessage: serverError,
  formId = 'offer-edit-form',
  onDeactivateClick,
  onSubmit,
}: OfferEditFormProps) {
  const [values, setValues] = useState<OfferEditValues>({
    salePrice: offer.salePrice,
    initialStock: offer.initialStock,
    salesEnd: offer.salesEnd,
    pickupStart: offer.pickupStart,
    pickupEnd: offer.pickupEnd,
  });

  const floor = quantityFloor(offer);
  const changes = diffOfferChanges(offer, values);
  const changed = hasChanges(changes);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!changed || isPending || isLocked) return;
    await onSubmit(values);
  };

  const isFormBlocked = !changed || isPending || isLocked;

  return (
    <form id={formId} onSubmit={handleSubmit} className="split h">
      <div style={{ display: 'grid', gap: 'var(--s2)', alignContent: 'start' }}>
        <div className="box" style={{ background: 'var(--fill)' }}>
          <div className="t">{offer.productName}</div>
          <div className="m">
            {offer.status} · 최초 수량 {offer.initialStock}개 (남은 {offer.remainingStock}개)
          </div>
        </div>

        <Input
          label={`할인가 (정가 ${formatWon(offer.originalPrice)}보다 낮게) *`}
          type="number"
          value={values.salePrice ? String(values.salePrice) : ''}
          readOnly={isPending || isLocked}
          onChange={(val) =>
            setValues((prev) => ({
              ...prev,
              salePrice: Number(val) || 0,
            }))
          }
        />

        <div>
          <div className="lbl">최초 수량 (최소 {floor}개) *</div>
          <Stepper
            value={values.initialStock}
            min={floor}
            max={9999}
            disabled={isPending || isLocked}
            onChange={(val) => setValues((prev) => ({ ...prev, initialStock: val }))}
            style={{ justifyContent: 'space-between' }}
          />
        </div>

        <div>
          <div className="lbl">일정 변경</div>
          <OfferScheduleFields
            salesStart={offer.salesStart}
            salesEnd={values.salesEnd}
            pickupStart={values.pickupStart}
            pickupEnd={values.pickupEnd}
            now={now}
            disabled={isPending || isLocked}
            onSalesEndChange={(val) => setValues((prev) => ({ ...prev, salesEnd: val }))}
            onPickupStartChange={(val) => setValues((prev) => ({ ...prev, pickupStart: val }))}
            onPickupEndChange={(val) => setValues((prev) => ({ ...prev, pickupEnd: val }))}
          />
        </div>
      </div>

      <div style={{ display: 'grid', gap: 'var(--s2)', alignContent: 'start' }}>
        {isLocked ? (
          <div>
            <div className="lbl">예약이 생긴 할인을 열면</div>
            <div className="warn">{OWNER_OFFER_MESSAGES.EDIT_LOCKED_NOTICE}</div>
            {onDeactivateClick && (
              <div className="row" style={{ marginTop: 'var(--s2)' }}>
                <Button size="sm" onClick={onDeactivateClick}>
                  판매 중단 (O5)
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div>
            <div className="m" style={{ color: 'var(--mute)' }}>
              할인 정보를 수정한 뒤 저장을 눌러주세요.
            </div>
            {onDeactivateClick && (
              <div className="row" style={{ marginTop: 'var(--s2)' }}>
                <Button size="sm" onClick={onDeactivateClick}>
                  판매 중단 (O5)
                </Button>
              </div>
            )}
          </div>
        )}

        {serverError ? <FieldError>{serverError}</FieldError> : null}

        <Button
          type="submit"
          variant="primary"
          desktopOnly
          pending={isPending}
          disabled={isFormBlocked}
          style={{ width: '100%', marginTop: 'var(--s2)' }}
        >
          저장
        </Button>
      </div>
    </form>
  );
}
