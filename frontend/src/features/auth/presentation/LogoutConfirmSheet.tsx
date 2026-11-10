import { useEffect, useId, useRef, useState } from 'react';
import { useAuth } from '../application/authContext';

export function LogoutConfirmSheet({ onClose }: { onClose(): void }) {
  const { logout } = useAuth();
  const titleId = useId();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const submitting = useRef(false);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  async function confirm() {
    if (submitting.current) return;
    submitting.current = true;
    setPending(true);
    await logout();
    onClose();
  }

  return (
    <div className="sheet" role="alertdialog" aria-modal="true" aria-labelledby={titleId}>
      <div className="t" id={titleId}>
        로그아웃할까요?
      </div>
      <button
        type="button"
        className="btn dark"
        aria-disabled={pending ? 'true' : undefined}
        onClick={() => void confirm()}
      >
        {pending ? '처리 중…' : '로그아웃'}
      </button>
      <button type="button" className="btn" ref={cancelRef} onClick={onClose}>
        취소
      </button>
    </div>
  );
}
