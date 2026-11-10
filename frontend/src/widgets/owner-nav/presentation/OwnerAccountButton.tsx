import { useState } from 'react';
import { LogoutConfirmSheet } from '@/features/auth';
import { useOwnerDialog } from './useOwnerDialog';
import { OwnerAccountMenu } from './OwnerAccountMenu';

export function OwnerAccountButton() {
  const [showLogout, setShowLogout] = useState(false);
  // 다시 열 때는 처음 상태(계정 메뉴)부터 시작한다.
  const { triggerProps, close, layer } = useOwnerDialog(() => setShowLogout(false));

  return (
    <>
      <button type="button" className="acct" {...triggerProps}>
        계정
      </button>
      {layer(
        showLogout ? (
          <LogoutConfirmSheet onClose={close} />
        ) : (
          <OwnerAccountMenu onLogout={() => setShowLogout(true)} />
        ),
      )}
    </>
  );
}
