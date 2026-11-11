import { useState, type FormEvent } from 'react';
import { Button } from '@/shared/ui/Button';
import { FieldError } from '@/shared/ui/FieldError';
import { validatePickupCode } from '../domain/pickupCode';

// FIXME: 픽업 제출이 연결되지 않았다. 코드를 입력해도 픽업 완료가 처리되지 않는다
//   왜: 코드만으로 픽업하는 API가 없다 (owner-today.md B-2, Q-1)
//   언제: 결정 후 (사용자: 픽업 제출 방식), 늦어도 배포 전
export type PickupCodeFormProps = {
  variant?: 'panel' | 'cta';
  isPending?: boolean;
  errorMessage?: string | null;
  onSubmit: (code: string) => Promise<boolean>;
};

export function PickupCodeForm({
  variant = 'panel',
  isPending,
  errorMessage: serverError,
  onSubmit,
}: PickupCodeFormProps) {
  const [code, setCode] = useState<string>('');

  const issue = validatePickupCode(code);
  let clientError: string | null = null;
  if (code.trim() !== '' && issue === 'too-long') {
    clientError = '코드는 20자 이내로 입력해 주세요.';
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (issue !== null || isPending) return;
    const ok = await onSubmit(code);
    if (ok) {
      setCode('');
    }
  };

  const displayError = clientError ?? serverError;

  if (variant === 'cta') {
    return (
      <form onSubmit={handleSubmit} style={{ width: '100%', display: 'grid', gap: 'var(--s1)' }}>
        <div className="m">고객 화면의 픽업 코드 입력</div>
        <div className="row" style={{ flexWrap: 'nowrap', gap: 'var(--s2)' }}>
          <input
            className="in"
            type="text"
            value={code}
            maxLength={20}
            readOnly={isPending}
            placeholder="A12345"
            onChange={(e) => setCode(e.target.value)}
            style={{
              flex: 1,
              font: '600 18px var(--mono)',
              letterSpacing: '.12em',
              color: 'var(--fg)',
            }}
          />
          <Button
            type="submit"
            variant="primary"
            pending={isPending}
            disabled={issue !== null}
            style={{ flex: '0 0 auto' }}
          >
            픽업 완료
          </Button>
        </div>
        {displayError ? <FieldError>{displayError}</FieldError> : null}
      </form>
    );
  }

  // variant === 'panel' (PC 우측 패널)
  return (
    <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 'var(--s2)', width: '100%' }}>
      <div className="t">픽업 코드 입력</div>
      <div className="m">고객 화면의 코드를 입력해야 픽업 완료돼요.</div>
      <input
        className="in"
        type="text"
        value={code}
        maxLength={20}
        readOnly={isPending}
        placeholder="A12345"
        onChange={(e) => setCode(e.target.value)}
        style={{
          font: '600 22px var(--mono)',
          letterSpacing: '.15em',
          textAlign: 'center',
          color: 'var(--fg)',
        }}
      />
      {displayError ? <FieldError>{displayError}</FieldError> : null}
      <Button
        type="submit"
        variant="primary"
        pending={isPending}
        disabled={issue !== null}
        style={{ width: '100%' }}
      >
        픽업 완료
      </Button>
    </form>
  );
}
