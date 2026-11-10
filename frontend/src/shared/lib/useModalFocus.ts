import type { RefObject } from 'react';

// 시트 포커스: 첫 포커스, Tab 순환, Escape → onClose (customer-home.md §2.1)
export function useModalFocus(ref: RefObject<HTMLElement | null>, onClose: () => void): void {
  void ref;
  void onClose;
  throw new Error('not implemented: useModalFocus');
}
