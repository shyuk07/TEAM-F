import { useEffect, useRef, type CSSProperties, type KeyboardEvent, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

const OVERLAY_STYLE: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 10,
  width: '100%',
  maxWidth: 'var(--customer-pc-w)',
  margin: '0 auto',
  boxSizing: 'border-box',
};
const SHEET_STYLE: CSSProperties = {
  maxHeight: '100%',
  overflowY: 'auto',
  boxSizing: 'border-box',
};
const FOCUSABLE =
  'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function focusableElements(dialog: HTMLElement): HTMLElement[] {
  return Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (element) => element.closest('[hidden], [aria-hidden="true"]') === null,
  );
}

function restoreFocus(trigger: HTMLElement | null) {
  const currentTrigger = trigger?.isConnected
    ? trigger
    : Array.from(document.querySelectorAll<HTMLElement>('button')).find(
        (element) =>
          trigger !== null &&
          element.textContent === trigger.textContent &&
          element.getAttribute('aria-label') === trigger.getAttribute('aria-label'),
      );
  const target = currentTrigger ?? document.querySelector<HTMLElement>('h1, [role="heading"]');
  if (!target) return;
  const tabIndex = target.getAttribute('tabindex');
  if (!currentTrigger) target.setAttribute('tabindex', '-1');
  target.focus({ preventScroll: true });
  if (!currentTrigger) {
    if (tabIndex === null) target.removeAttribute('tabindex');
    else target.setAttribute('tabindex', tabIndex);
  }
}

export function ReservationModal({
  labelledBy,
  onDismiss,
  children,
}: {
  labelledBy: string;
  onDismiss(): void;
  children: ReactNode;
}) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const overlay = overlayRef.current;
    const dialog = dialogRef.current;
    if (!overlay || !dialog) return;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const background = Array.from(document.body.children)
      .filter((element) => element !== overlay)
      .map((element) => ({ element, inert: element.getAttribute('inert') }));
    const overflow = document.body.style.overflow;
    (focusableElements(dialog)[0] ?? dialog).focus();
    for (const { element } of background) element.setAttribute('inert', '');
    document.body.style.overflow = 'hidden';
    return () => {
      for (const { element, inert } of background) {
        if (inert === null) element.removeAttribute('inert');
        else element.setAttribute('inert', inert);
      }
      document.body.style.overflow = overflow;
      restoreFocus(trigger);
    };
  }, []);

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.preventDefault();
      onDismiss();
    } else if (event.key === 'Tab' && dialogRef.current) {
      event.preventDefault();
      const elements = focusableElements(dialogRef.current);
      const current = elements.findIndex((element) => element === document.activeElement);
      const next = event.shiftKey
        ? (current <= 0 ? elements.length : current) - 1
        : (current + 1) % elements.length;
      (elements[next] ?? dialogRef.current).focus();
    }
  }

  return createPortal(
    <div className="dim" ref={overlayRef} style={OVERLAY_STYLE}>
      <div
        className="sheet"
        ref={dialogRef}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        tabIndex={-1}
        style={SHEET_STYLE}
        onKeyDown={handleKeyDown}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}
