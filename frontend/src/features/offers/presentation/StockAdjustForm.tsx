import { useState, type FormEvent } from 'react';
import { Button } from '@/shared/ui/Button';
import { Chip } from '@/shared/ui/Chip';
import { FieldError } from '@/shared/ui/FieldError';
import { Input } from '@/shared/ui/Input';
import { Stepper } from '@/shared/ui/Stepper';
import type { Offer } from '../domain/offer';
import {
  amountBounds,
  stockAfter,
  validateStockAdjust,
  type StockMode,
} from '../domain/stockAdjustment';

export type StockAdjustFormProps = {
  offer: Offer;
  isPending?: boolean;
  errorMessage?: string | null;
  onSubmit: (mode: StockMode, amount: number, reason?: string) => Promise<void>;
  onCancel?: () => void;
};

export function StockAdjustForm({
  offer,
  isPending,
  errorMessage: serverError,
  onSubmit,
  onCancel,
}: StockAdjustFormProps) {
  const [mode, setMode] = useState<StockMode>('subtract');
  const [amount, setAmount] = useState<number>(1);
  const [reason, setReason] = useState<string>('');

  const bounds = amountBounds(offer, mode);
  const currentStockAfter = stockAfter(offer, mode, amount);
  const clientIssue = validateStockAdjust(offer, mode, amount, reason);

  let clientErrorMessage: string | null = null;
  if (clientIssue === 'over-remaining') {
    clientErrorMessage = '남은 재고보다 많이 뺄 수 없어요.';
  } else if (clientIssue === 'over-max') {
    clientErrorMessage = '최대 수량(9,999)을 초과할 수 없어요.';
  } else if (clientIssue === 'reason-too-long') {
    clientErrorMessage = '사유는 200자 이내로 입력해 주세요.';
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (clientIssue !== null || isPending) return;
    await onSubmit(mode, amount, reason);
  };

  const displayError = clientErrorMessage ?? serverError;

  return (
    <form onSubmit={handleSubmit} className="grid">
      <div>
        <div className="t">재고 조정</div>
        <div className="m">
          {offer.productName} · 지금 남은 {offer.remainingStock}개
        </div>
      </div>

      <div className="scroll" role="group" aria-label="조정 방식 선택">
        <Chip
          selected={mode === 'subtract'}
          onClick={() => {
            setMode('subtract');
            setAmount(1);
          }}
        >
          빼기 (파손·소진)
        </Chip>
        <Chip
          selected={mode === 'add'}
          onClick={() => {
            setMode('add');
            setAmount(1);
          }}
        >
          더하기 (추가 입고)
        </Chip>
      </div>

      <div className="lbl">수량</div>
      <Stepper
        value={amount}
        min={bounds.min}
        max={Math.max(bounds.min, bounds.max)}
        onChange={setAmount}
        disabled={isPending || bounds.max < bounds.min}
        className="kv"
      />

      <Input
        label="사유 (선택, 200자)"
        value={reason}
        maxLength={200}
        onChange={setReason}
        readOnly={isPending}
      />

      <div className="m">
        조정 후 남은 재고 <b>{currentStockAfter}개</b>
      </div>

      {displayError ? <FieldError>{displayError}</FieldError> : null}

      <div className="row" style={{ marginTop: 'var(--s1)' }}>
        {onCancel && (
          <Button onClick={onCancel} disabled={isPending}>
            취소
          </Button>
        )}
        <Button
          type="submit"
          variant="primary"
          pending={isPending}
          disabled={clientIssue !== null || bounds.max < bounds.min}
          style={{ flex: 1 }}
        >
          적용
        </Button>
      </div>
    </form>
  );
}
