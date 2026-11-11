import { useEffect, useRef, type RefObject } from 'react';

const FOCUSABLE =
  'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// 시트 포커스: 첫 포커스, Tab 순환, Escape → onClose (customer-home.md §2.1)
export function useModalFocus(ref: RefObject<HTMLElement | null>, onClose: () => void): void {
  // onClose가 렌더마다 새로 만들어져도 첫 포커스를 다시 옮기지 않도록 최신 값만 ref에 둔다.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const items = () => Array.from(ref.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
    // 안쪽 컴포넌트가 이미 포커스를 정했으면(예: 로그아웃 확인의 「취소」) 덮어쓰지 않는다
    if (!ref.current?.contains(document.activeElement)) items()[0]?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCloseRef.current();
        return;
      }
      if (e.key !== 'Tab') return;
      // 포커스 트랩: Tab·Shift+Tab이 ref 안에서만 돈다(aria-modal).
      const list = items();
      if (list.length === 0) return;
      const first = list[0];
      const last = list[list.length - 1];
      const active = document.activeElement;
      const inside = active instanceof HTMLElement && list.includes(active);
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
  }, [ref]);
}
