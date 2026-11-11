import { useCallback, useRef, useState, type ReactNode } from 'react';
import { Overlay } from '@/shared/ui/Overlay';

// OwnerLogoutLink·OwnerAccountButton이 함께 쓰는 다이얼로그 상태 훅(stores.md §6).
// 닫히면 Overlay가 숨김을 풀고 난 뒤 원래 버튼으로 포커스를 되돌린다(app-shell.md D-21, D-23).
// onOpen은 버튼이 다시 열릴 때 추가로 할 일.
export function useOwnerDialog(onOpen?: () => void) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const close = useCallback(() => setOpen(false), []);

  const openDialog = () => {
    onOpen?.();
    setOpen(true);
  };

  const triggerProps = {
    ref: buttonRef,
    'aria-haspopup': 'dialog' as const,
    'aria-expanded': open,
    onClick: openDialog,
  };

  // 액션 시트(계정 메뉴·로그아웃)는 모바일 폭으로 제한해 하단 중앙에 배치한다.
  const layer = (content: ReactNode) =>
    open ? (
      <Overlay onClose={close} returnFocusRef={buttonRef}>
        <div style={{ width: '100%', maxWidth: 'var(--customer-pc-w)', alignSelf: 'center' }}>
          {content}
        </div>
      </Overlay>
    ) : null;

  return { triggerProps, close, layer };
}
