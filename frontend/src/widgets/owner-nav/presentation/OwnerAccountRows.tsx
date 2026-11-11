import { Link, useLocation } from 'react-router';
import { LogoutConfirmSheet } from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';
import { useOwnerDialog } from './useOwnerDialog';

// O4 매장 탭 아래 「계정」 행(비밀번호 변경 → C9, 로그아웃 → C10). 모바일 매장 탭에만 둔다(`.mob`: 720px 이상에서 숨김, PC는 우측 상단 「계정」 버튼).
export function OwnerAccountRows() {
  const location = useLocation();
  const { triggerProps, close, layer } = useOwnerDialog();
  // C9의 ← 가 지금 화면으로 돌아오게 한다(auth-account.md D-23).
  const linkState = { from: location.pathname + location.search + location.hash };

  return (
    <>
      <div className="mob">
        <div style={{ display: 'grid', gap: 'var(--s3)' }}>
          <div className="lbl" style={{ marginTop: 'var(--s4)' }}>
            계정
          </div>
          <Link className="li" to={ROUTES.accountPassword} state={linkState}>
            <span>비밀번호 변경</span>
            <span className="m">›</span>
          </Link>
          <button type="button" className="li" {...triggerProps}>
            <span>로그아웃</span>
            <span className="m">›</span>
          </button>
        </div>
      </div>
      {layer(<LogoutConfirmSheet onClose={close} />)}
    </>
  );
}
