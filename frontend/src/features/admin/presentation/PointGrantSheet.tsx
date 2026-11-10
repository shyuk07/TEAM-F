import { useId, useState, type FormEvent } from 'react';
import { Overlay } from '@/shared/ui/Overlay';
import { useAdminMutation } from '../application/useAdminMutation';
import { formatPoint } from '../domain/labels';
import {
  balanceAfterGrant,
  grantButtonLabel,
  grantErrorMessage,
  parseAmount,
  validateGrant,
} from '../domain/pointGrant';

export type GrantTarget = { id: string; name: string; email: string; balance: number };

// M4 포인트 지급. 버튼 문구에 금액을 넣는다. 회수(음수) 기능은 없다 (screens.md M4).
export function PointGrantSheet({
  target,
  onClose,
  onDone,
}: {
  target: GrantTarget;
  onClose(): void;
  onDone(balanceAfter: number | null): void;
}) {
  const titleId = useId();
  const amountId = useId();
  const reasonId = useId();
  const [amountText, setAmountText] = useState('');
  const [reason, setReason] = useState('');
  const [inputError, setInputError] = useState<string | null>(null);
  const { run, pending, error } = useAdminMutation();

  const amount = parseAmount(amountText);
  const submitLabel = grantButtonLabel(amount);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (pending) return;
    const v = validateGrant(amountText, reason);
    if (!v.ok) {
      setInputError(grantErrorMessage(v.error));
      return;
    }
    setInputError(null);
    const outcome = await run((admin) =>
      admin.grantPoints(target.id, v.value.amount, v.value.reason),
    );
    if (outcome.ok) onDone(outcome.value.balanceAfter);
  }

  const shownError = inputError ?? error;

  return (
    <Overlay onClose={onClose} dismissible={!pending}>
      <form
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        noValidate
        onSubmit={(e) => void onSubmit(e)}
      >
        <div className="t" id={titleId} style={{ fontSize: 17 }}>
          포인트 지급
        </div>
        <div className="box">
          <div className="t">{`대상: ${target.name}`}</div>
          <div className="m">{target.email}</div>
          <div className="kv">
            <span>현재 잔액</span>
            <b>{formatPoint(target.balance)}</b>
          </div>
        </div>
        <label className="lbl" htmlFor={amountId}>
          지급 포인트 * (1 이상)
        </label>
        <input
          id={amountId}
          data-autofocus
          className="in"
          inputMode="numeric"
          style={{ color: 'var(--fg)' }}
          value={amountText}
          aria-required="true"
          onChange={(e) => setAmountText(e.target.value)}
        />
        <label className="lbl" htmlFor={reasonId}>
          지급 사유 *
        </label>
        <textarea
          id={reasonId}
          className="in"
          style={{ minHeight: 64, paddingBlock: 'var(--s2)', color: 'var(--fg)', font: 'inherit' }}
          value={reason}
          aria-required="true"
          onChange={(e) => setReason(e.target.value)}
        />
        <div className="m">
          지급 후 잔액 <b>{formatPoint(balanceAfterGrant(target.balance, amount))}</b> · 회원 내역에
          &quot;지급&quot;으로 남아요.
        </div>
        {shownError !== null ? (
          <div className="err" role="alert">
            {shownError}
          </div>
        ) : null}
        <div className="row" style={{ flexWrap: 'nowrap' }}>
          <button
            type="button"
            className="btn"
            style={{ flex: 1 }}
            disabled={pending}
            onClick={onClose}
          >
            취소
          </button>
          <button
            type="submit"
            className="btn pri"
            style={{ flex: 1 }}
            aria-disabled={pending ? 'true' : undefined}
          >
            {pending ? '처리 중…' : submitLabel}
          </button>
        </div>
      </form>
    </Overlay>
  );
}
