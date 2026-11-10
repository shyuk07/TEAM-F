import { useRef, useState } from 'react';
import { LogoutConfirmSheet } from '@/features/auth';
import { OwnerDialogLayer } from './OwnerDialogLayer';

// O0 상단 텍스트 링크 「로그아웃」(screens.md O0, stores.md §6). 누르면 확인 시트를 열고,
// 취소·Esc로 닫으면 링크로 포커스가 돌아온다.
export function OwnerLogoutLink() {
  const [open, setOpen] = useState(false);
  // 시트를 그릴 앱 프레임. 렌더 중에 ref를 읽지 않도록 열 때 정해 둔다(OwnerAccountButton 방식).
  const [target, setTarget] = useState<Element | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const close = () => {
    setOpen(false);
    buttonRef.current?.focus();
  };

  return (
    <>
      <button
        type="button"
        className="link"
        ref={buttonRef}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => {
          setTarget(buttonRef.current?.closest('.app') ?? document.body);
          setOpen(true);
        }}
      >
        로그아웃
      </button>
      {open && target !== null ? (
        <OwnerDialogLayer target={target} onClose={close}>
          <LogoutConfirmSheet onClose={close} />
        </OwnerDialogLayer>
      ) : null}
    </>
  );
}
