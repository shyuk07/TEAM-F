import { useCallback, useRef, useState, type ReactNode } from 'react';
import { OwnerDialogLayer } from './OwnerDialogLayer';

// OwnerLogoutLink·OwnerAccountButton이 함께 쓰는 다이얼로그 상태 훅(stores.md §6).
// 열 때 트리거 버튼의 .app 조상을 타깃으로 정해 두고(렌더 중 ref 읽기 방지),
// 닫히면 원래 버튼으로 포커스를 되돌린다. onOpen은 버튼이 다시 열릴 때 추가로 할 일.
export function useOwnerDialog(onOpen?: () => void) {
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState<Element | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const close = useCallback(() => {
    setOpen(false);
    buttonRef.current?.focus();
  }, []);

  const openDialog = () => {
    onOpen?.();
    setTarget(buttonRef.current?.closest('.app') ?? document.body);
    setOpen(true);
  };

  const triggerProps = {
    ref: buttonRef,
    'aria-haspopup': 'dialog' as const,
    'aria-expanded': open,
    onClick: openDialog,
  };

  // 열려 있고 타깃이 정해졌을 때만 .app 안으로 포털한다. 그 외에는 아무것도 그리지 않는다.
  const layer = (content: ReactNode) =>
    open && target !== null ? (
      <OwnerDialogLayer target={target} onClose={close}>
        {content}
      </OwnerDialogLayer>
    ) : null;

  return { triggerProps, close, layer };
}
