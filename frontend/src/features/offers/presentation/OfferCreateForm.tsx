import { useState, type FormEvent } from 'react';
import type { Product } from '@/entities/product';
import { Button } from '@/shared/ui/Button';
import { Chip } from '@/shared/ui/Chip';
import { FieldError } from '@/shared/ui/FieldError';
import { Input } from '@/shared/ui/Input';
import { Stepper } from '@/shared/ui/Stepper';
import { formatHm, formatWon } from '../domain/offerFormat';
import {
  applyQuickPick,
  cancelDeadline,
  isCancelBlocked,
  QUICK_PICKS,
  quickPickLabel,
  validateDraft,
  type OfferDraft,
} from '../domain/offerDraft';
import { OfferScheduleFields } from './OfferScheduleFields';

export type OfferCreateFormProps = {
  products: Product[];
  initialDraft: OfferDraft;
  now: Date;
  isPending?: boolean;
  errorMessage?: string | null;
  submitButtonText?: string;
  formId?: string;
  onSubmit: (draft: OfferDraft) => Promise<void>;
};

export function OfferCreateForm({
  products,
  initialDraft,
  now,
  isPending,
  errorMessage: serverError,
  submitButtonText = '할인 등록',
  formId = 'offer-create-form',
  onSubmit,
}: OfferCreateFormProps) {
  const [draft, setDraft] = useState<OfferDraft>(initialDraft);
  const [customSchedule, setCustomSchedule] = useState<boolean>(
    initialDraft.quickPick === 'custom',
  );

  const selectedProduct = products.find((p) => p.id === draft.productId);
  const originalPrice = selectedProduct?.originalPrice ?? 0;

  const issues = validateDraft(draft, originalPrice, now);
  const cancelBlocked = isCancelBlocked(draft, now);
  const deadline = cancelDeadline(draft);

  const handleProductChange = (productId: string) => {
    const prod = products.find((p) => p.id === productId);
    setDraft((prev) => ({
      ...prev,
      productId,
      // open-issues: 할인가 기본 자동 계산(정가의 30% 할인)은 정본이 없어 0으로 비움 — 사용자가 직접 입력
      salePrice: prod ? 0 : prev.salePrice,
    }));
  };

  const handleQuickPick = (minutes: number) => {
    setDraft((prev) => applyQuickPick(prev, minutes, now));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (issues.length > 0 || isPending || !draft.productId) return;
    await onSubmit(draft);
  };

  const isFormBlocked = issues.length > 0 || !draft.productId || isPending;

  return (
    <form id={formId} onSubmit={handleSubmit} className="split h">
      <div className="grid">
        <div>
          <label className="lbl" htmlFor="offer-product-select">
            상품 *
          </label>
          <select
            id="offer-product-select"
            className="in"
            value={draft.productId}
            disabled={isPending}
            onChange={(e) => handleProductChange(e.target.value)}
          >
            <option value="">상품을 선택해 주세요</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({formatWon(p.originalPrice)})
              </option>
            ))}
          </select>
        </div>

        <div className="row">
          <div style={{ flex: 1 }}>
            <div className="lbl">정가</div>
            <div className="in ro">{originalPrice > 0 ? formatWon(originalPrice) : '0원'}</div>
          </div>
          <div style={{ flex: 1 }}>
            <Input
              label="할인가 *"
              type="number"
              value={draft.salePrice ? String(draft.salePrice) : ''}
              readOnly={isPending}
              onChange={(val) =>
                setDraft((prev) => ({
                  ...prev,
                  salePrice: Number(val) || 0,
                }))
              }
            />
          </div>
        </div>

        <div>
          <div className="lbl">수량 * (1~9999)</div>
          <Stepper
            value={draft.initialStock}
            min={1}
            max={9999}
            disabled={isPending}
            onChange={(val) => setDraft((prev) => ({ ...prev, initialStock: val }))}
            className="kv"
          />
        </div>

        <div>
          <div className="lbl">픽업 시작 · 빠른 선택</div>
          <div className="scroll" role="group" aria-label="빠른 픽업 시작 선택">
            {QUICK_PICKS.map((mins) => (
              <Chip
                key={mins}
                selected={draft.quickPick === mins && !customSchedule}
                onClick={() => {
                  setCustomSchedule(false);
                  handleQuickPick(mins);
                }}
              >
                {quickPickLabel(mins)}
              </Chip>
            ))}
            <Chip
              selected={customSchedule}
              onClick={() => {
                const nextCustom = !customSchedule;
                setCustomSchedule(nextCustom);
                if (nextCustom) {
                  setDraft((prev) => ({ ...prev, quickPick: 'custom' }));
                }
              }}
            >
              직접 입력
            </Chip>
          </div>
        </div>

        {customSchedule && (
          <div style={{ marginTop: 'var(--s1)' }}>
            <OfferScheduleFields
              salesStart={draft.salesStart}
              salesEnd={draft.salesEnd}
              pickupStart={draft.pickupStart}
              pickupEnd={draft.pickupEnd}
              now={now}
              disabled={isPending}
              onSalesStartChange={(val) => setDraft((prev) => ({ ...prev, salesStart: val }))}
              onSalesEndChange={(val) => setDraft((prev) => ({ ...prev, salesEnd: val }))}
              onPickupStartChange={(val) => setDraft((prev) => ({ ...prev, pickupStart: val }))}
              onPickupEndChange={(val) => setDraft((prev) => ({ ...prev, pickupEnd: val }))}
            />
          </div>
        )}
      </div>

      <div className="grid">
        <div className="box" style={{ background: 'var(--fill)' }}>
          <div className="kv">
            <span className="lbl">판매</span>
            <b>
              {draft.salesStart === 'now' ? '지금' : `오늘 ${formatHm(draft.salesStart)}`} →{' '}
              {formatHm(draft.salesEnd)}
            </b>
          </div>
          <div className="kv">
            <span className="lbl">픽업</span>
            <b>
              오늘 {formatHm(draft.pickupStart)} → {formatHm(draft.pickupEnd)}
            </b>
          </div>
          <div className="kv">
            <span className="lbl">고객 취소 가능</span>
            <b>{cancelBlocked ? '취소 불가 (1시간 이내)' : `${formatHm(deadline)}까지`}</b>
          </div>
          <button type="button" className="link" onClick={() => setCustomSchedule(!customSchedule)}>
            시간 직접 바꾸기
          </button>
        </div>

        {cancelBlocked && (
          <div className="warn">
            취소 마감(픽업 시작 1시간 전)이 이미 지나 고객이 예약을 취소할 수 없어요.
          </div>
        )}

        {serverError ? <FieldError>{serverError}</FieldError> : null}

        <Button
          type="submit"
          variant="primary"
          desktopOnly
          pending={isPending}
          disabled={isFormBlocked}
          style={{ width: '100%' }}
        >
          {submitButtonText}
        </Button>
      </div>
    </form>
  );
}
