import { useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router';
import { roleLabel, useAuth } from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

// TODO: PC에서도 드롭다운 대신 시트를 쓴다.
//   왜: 드롭다운 컴포넌트가 디자인 시스템에 없다 (docs/design/frontend/auth.md D-3)
//   언제: 결정 후 (사용자: PC 드롭다운)
// open-issues: O8 상점주 회원 탈퇴 메뉴 없음 (규칙이 정해질 때까지 메뉴에서 뺌)
export function OwnerAccountMenu({ onLogout }: { onLogout(): void }) {
  const { state } = useAuth();
  const location = useLocation();
  const user = state.status === 'authenticated' ? state.user : null;
  const firstRef = useRef<HTMLAnchorElement>(null);
  // C8·C9의 ← 가 지금 화면으로 돌아오게 한다(auth-account.md D-23).
  const linkState = { from: location.pathname + location.search + location.hash };

  useEffect(() => {
    firstRef.current?.focus();
  }, []);

  return (
    <div className="sheet" role="dialog" aria-modal="true" aria-label="계정 메뉴">
      {user !== null ? (
        <div>
          <div className="t">{user.name ?? user.email}</div>
          <div className="m">{`${user.email} · ${roleLabel(user.role)}`}</div>
        </div>
      ) : null}
      <div className="list">
        <Link className="li" to={ROUTES.accountProfile} state={linkState} ref={firstRef}>
          <span>내 정보 (전화번호)</span>
          <span className="m">›</span>
        </Link>
        <Link className="li" to={ROUTES.accountPassword} state={linkState}>
          <span>비밀번호 변경</span>
          <span className="m">›</span>
        </Link>
        <button type="button" className="li" onClick={onLogout}>
          <span>로그아웃</span>
          <span className="m">›</span>
        </button>
      </div>
      {user?.role === 'OWNER' ? (
        <div className="m">상점 정보·폐점은 매장 탭(O4)에 있어요.</div>
      ) : null}
    </div>
  );
}
