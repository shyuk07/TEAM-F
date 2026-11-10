import { LogoutConfirmSheet } from '@/features/auth';
import { useOwnerDialog } from './useOwnerDialog';

// O0 상단 텍스트 링크 「로그아웃」(screens.md O0, stores.md §6). 누르면 확인 시트를 열고,
// 취소·Esc로 닫으면 링크로 포커스가 돌아온다.
export function OwnerLogoutLink() {
  const { triggerProps, close, layer } = useOwnerDialog();

  return (
    <>
      <button type="button" className="link" {...triggerProps}>
        로그아웃
      </button>
      {layer(<LogoutConfirmSheet onClose={close} />)}
    </>
  );
}
