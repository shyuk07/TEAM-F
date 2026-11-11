import { useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

const FOCUSABLE =
  'button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// 앱 프레임(.app)에 딤과 시트를 띄운다. Esc·딤 클릭으로 닫고, Tab은 시트 안에서만 돈다.
// 열리면 data-autofocus 요소(없으면 첫 포커스 가능 요소)에 포커스를 주고,
// 닫히면 열기 직전에 포커스가 있던 요소로 돌려준다(그 요소가 사라졌으면 앱 프레임으로).
// dismissible=false(처리 중)이면 Esc·딤 클릭으로 닫지 않는다.
export function Overlay({
  onClose,
  dismissible = true,
  children,
}: {
  onClose(): void;
  dismissible?: boolean;
  children: ReactNode;
}) {
  const anchorRef = useRef<HTMLSpanElement>(null);
  const dimRef = useRef<HTMLDivElement>(null);
  const [target, setTarget] = useState<Element | null>(null);
  const onCloseRef = useRef(onClose);
  const dismissibleRef = useRef(dismissible);

  useEffect(() => {
    onCloseRef.current = onClose;
    dismissibleRef.current = dismissible;
  });

  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const frame = anchorRef.current?.closest<HTMLElement>('.app') ?? null;
    setTarget(frame ?? document.body);
    return () => {
      if (opener?.isConnected) {
        opener.focus();
      } else if (frame?.isConnected) {
        frame.tabIndex = -1;
        frame.focus();
      }
    };
  }, []);

  useEffect(() => {
    if (target === null) return;
    const root = dimRef.current;
    const initial =
      root?.querySelector<HTMLElement>('[data-autofocus]') ??
      root?.querySelector<HTMLElement>(FOCUSABLE) ??
      null;
    initial?.focus();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (dismissibleRef.current) onCloseRef.current();
        return;
      }
      if (e.key !== 'Tab') return;
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
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [target]);

  return (
    <>
      <span ref={anchorRef} hidden />
      {target !== null
        ? createPortal(
            <div
              className="dim"
              ref={dimRef}
              onClick={(e) => {
                if (e.target === e.currentTarget && dismissibleRef.current) onCloseRef.current();
              }}
            >
              {children}
            </div>,
            target,
          )
        : null}
    </>
  );
}
