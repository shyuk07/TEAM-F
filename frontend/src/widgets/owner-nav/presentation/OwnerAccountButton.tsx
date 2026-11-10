import { useRef, useState } from 'react';
import { LogoutConfirmSheet } from '@/features/auth';
import { OwnerDialogLayer } from './OwnerDialogLayer';
import { OwnerAccountMenu } from './OwnerAccountMenu';

type MenuState = 'closed' | 'account' | 'logout';

export function OwnerAccountButton() {
  const [menu, setMenu] = useState<MenuState>('closed');
  // 시트를 그릴 앱 프레임. 렌더 중에 ref를 읽지 않도록 열 때 정해 둔다.
  const [target, setTarget] = useState<Element | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const open = menu !== 'closed';

  const close = () => {
    setMenu('closed');
    buttonRef.current?.focus();
  };

  return (
    <>
      <button
        type="button"
        className="acct"
        ref={buttonRef}
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => {
          setTarget(buttonRef.current?.closest('.app') ?? document.body);
          setMenu('account');
        }}
      >
        계정
      </button>
      {open && target !== null ? (
        <OwnerDialogLayer target={target} onClose={close}>
          {menu === 'logout' ? (
            <LogoutConfirmSheet onClose={close} />
          ) : (
            <OwnerAccountMenu onLogout={() => setMenu('logout')} />
          )}
        </OwnerDialogLayer>
      ) : null}
    </>
  );
}
