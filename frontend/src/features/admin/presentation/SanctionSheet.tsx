import { useId, useState, type FormEvent, type ReactNode } from 'react';
import { Overlay } from '@/shared/ui/Overlay';
import { runSanction, type SanctionResult } from '../application/runSanction';
import { useAdminMutation } from '../application/useAdminMutation';
import {
  SUSPENSION_END_LABEL,
  hasSuspensionEnd,
  sanctionCopy,
  sanctionErrorMessage,
  validateSanction,
  type SanctionKind,
} from '../domain/sanction';

export type SanctionTarget = { id: string; label: string };

// M2 제재 확인. 동작(kind)은 열기 전에 정해지고 시트 안에서 바꿀 수 없다 (screens.md M2).
// TODO: M2 「진행 중 예약 N건」과 강제 폐점 전 「예약 취소·환불 건수」를 보여 주지 않는다.
//   왜: 그 건수를 주는 API가 없다 (docs/design/frontend/admin.md C-2)
//   언제: 백엔드 API 추가 후
export function SanctionSheet({
  kind,
  target,
  facts,
  onClose,
  onDone,
}: {
  kind: SanctionKind;
  target: SanctionTarget;
  facts?: ReactNode;
  onClose(): void;
  onDone(result: SanctionResult): void;
}) {
  const copy = sanctionCopy(kind);
  const titleId = useId();
  const reasonId = useId();
  const endId = useId();
  const [reason, setReason] = useState('');
  const [endDate, setEndDate] = useState('');
  const [inputError, setInputError] = useState<string | null>(null);
  const { run, pending, error } = useAdminMutation();

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (pending) return;
    const v = validateSanction(kind, { reason, endDate }, new Date());
    if (!v.ok) {
      setInputError(sanctionErrorMessage(v.error));
      return;
    }
    setInputError(null);
    const outcome = await run((admin) => runSanction({ admin }, kind, target.id, v.value));
    if (outcome.ok) onDone(outcome.value);
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
          {copy.title}
        </div>
        <div className="box">
          <div className="t">{`대상: ${target.label}`}</div>
          {facts}
        </div>
        <label className="lbl" htmlFor={reasonId}>
          {copy.reasonLabel}
        </label>
        <textarea
          id={reasonId}
          data-autofocus
          className="in"
          style={{ minHeight: 64, paddingBlock: 'var(--s2)', color: 'var(--fg)', font: 'inherit' }}
          value={reason}
          aria-required="true"
          onChange={(e) => setReason(e.target.value)}
        />
        {hasSuspensionEnd(kind) ? (
          <>
            <label className="lbl" htmlFor={endId}>
              {SUSPENSION_END_LABEL}
            </label>
            <input
              id={endId}
              className="in"
              type="date"
              style={{ color: 'var(--fg)' }}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </>
        ) : null}
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
            className="btn dark"
            style={{ flex: 1 }}
            aria-disabled={pending ? 'true' : undefined}
          >
            {pending ? '처리 중…' : copy.submitLabel}
          </button>
        </div>
      </form>
    </Overlay>
  );
}
