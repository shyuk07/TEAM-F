import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import { createPortal } from 'react-dom';
import { openShellOverlay } from '@/shared/lib/shellOverlay';

const FOCUSABLE =
  'button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// 앱 프레임(.app)에 딤과 시트를 띄운다. Esc·딤 클릭으로 닫고, Tab은 시트 안에서만 돈다.
// 열리면 data-autofocus 요소(없으면 첫 포커스 가능 요소)에 포커스를 주고,
// 닫히면 열기 직전에 포커스가 있던 요소로 돌려준다(그 요소가 사라졌으면 앱 프레임으로).
// dismissible=false(처리 중)이면 Esc·딤 클릭으로 닫지 않는다.
export function Overlay({
  onClose,
  dismissible = true,
  returnFocusRef,
  children,
}: {
  onClose(): void;
  dismissible?: boolean;
  // 닫힐 때 포커스를 돌려줄 요소. 없으면 열기 직전 activeElement (app-shell.md §11.4-7)
  returnFocusRef?: RefObject<HTMLElement | null>;
  children: ReactNode;
}) {
  const anchorRef = useRef<HTMLSpanElement>(null);
  const [dim, setDim] = useState<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  const dismissibleRef = useRef(dismissible);
  const returnFocusRefRef = useRef(returnFocusRef);

  useEffect(() => {
    onCloseRef.current = onClose;
    dismissibleRef.current = dismissible;
    returnFocusRefRef.current = returnFocusRef;
  });

  useEffect(() => {
    const anchor = anchorRef.current;
    if (!anchor) return;
    const active = document.activeElement;
    const opener = active instanceof HTMLElement && active !== document.body ? active : null;
    const handle = openShellOverlay(anchor);
    const onDimClick = (e: MouseEvent) => {
      if (e.target === handle.dim && dismissibleRef.current) onCloseRef.current();
    };
    handle.dim.addEventListener('click', onDimClick);
    setDim(handle.dim);
    return () => {
      handle.dim.removeEventListener('click', onDimClick);
      // 숨김 해제 뒤에 포커스를 돌려준다(D-23)
      handle.close(returnFocusRefRef.current?.current ?? opener);
    };
  }, []);

  useEffect(() => {
    if (dim === null) return;
    const root = dim;
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
      const items = Array.from(dim.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
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
  }, [dim]);

  return (
    <>
      <span ref={anchorRef} hidden />
      {dim !== null ? createPortal(children, dim) : null}
    </>
  );
}
