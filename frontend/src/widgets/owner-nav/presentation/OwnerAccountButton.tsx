import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { LogoutConfirmSheet } from '@/features/auth';
import { OwnerAccountMenu } from './OwnerAccountMenu';

const FOCUSABLE =
  'button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])';

type MenuState = 'closed' | 'account' | 'logout';

export function OwnerAccountButton() {
  const [menu, setMenu] = useState<MenuState>('closed');
  // 시트를 그릴 앱 프레임. 렌더 중에 ref를 읽지 않도록 열 때 정해 둔다.
  const [target, setTarget] = useState<Element | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dimRef = useRef<HTMLDivElement>(null);
  const open = menu !== 'closed';

  const close = () => {
    setMenu('closed');
    buttonRef.current?.focus();
  };

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        // 포커스 트랩: Tab·Shift+Tab이 시트 안에서만 돈다(aria-modal).
        const items = Array.from(dimRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
        if (items.length === 0) return;
        const first = items[0];
        const last = items[items.length - 1];
        const active = document.activeElement;
        const inside = active instanceof HTMLElement && items.includes(active);
        if (e.shiftKey && (active === first || !inside)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && (active === last || !inside)) {
          e.preventDefault();
          first.focus();
        }
        return;
      }
      if (e.key !== 'Escape') return;
      setMenu('closed');
      buttonRef.current?.focus();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open]);

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
      {open && target !== null
        ? createPortal(
            <div
              className="dim"
              ref={dimRef}
              onClick={(e) => {
                if (e.target === e.currentTarget) close();
              }}
            >
              {menu === 'logout' ? (
                <LogoutConfirmSheet onClose={close} />
              ) : (
                <OwnerAccountMenu onLogout={() => setMenu('logout')} />
              )}
            </div>,
            target,
          )
        : null}
    </>
  );
}
