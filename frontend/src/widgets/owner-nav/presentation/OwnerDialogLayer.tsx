import { useEffect, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

const FOCUSABLE =
  'button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])';

// OwnerAccountButton·OwnerLogoutLink가 함께 쓰는 오버레이(stores.md §6).
// .app 프레임 안으로 포털하고, Tab 포커스 트랩(aria-modal)과 Esc·배경 클릭 닫기를 맡는다.
// 닫기와 포커스 복원은 onClose에서 한다.
export function OwnerDialogLayer({
  target,
  onClose,
  children,
}: {
  target: Element;
  onClose(): void;
  children: ReactNode;
}) {
  const dimRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        // 포커스 트랩: Tab·Shift+Tab이 대화상자 안에서만 돈다(aria-modal).
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
      onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  return createPortal(
    <div
      className="dim"
      ref={dimRef}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {children}
    </div>,
    target,
  );
}
