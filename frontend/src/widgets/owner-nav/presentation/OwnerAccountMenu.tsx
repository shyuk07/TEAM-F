import { useEffect, useRef } from 'react';
import { roleLabel, useAuth } from '@/features/auth';

// TODO: 메뉴에 「내 정보」(C8)·「비밀번호 변경」(C9) 행이 없고, PC에서도 드롭다운 대신 시트를 쓴다.
//   왜: C8·C9 화면이 없고 드롭다운 컴포넌트가 디자인 시스템에 없다 (docs/design/frontend/auth.md D-3)
//   언제: C8 구현 시, C9 구현 시, 결정 후 (사용자: PC 드롭다운)
// open-issues: O8 상점주 회원 탈퇴 메뉴 없음 (규칙이 정해질 때까지 메뉴에서 뺌)
export function OwnerAccountMenu({ onLogout }: { onLogout(): void }) {
  const { state } = useAuth();
  const user = state.status === 'authenticated' ? state.user : null;
  const firstRef = useRef<HTMLButtonElement>(null);

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
        <button type="button" className="li" ref={firstRef} onClick={onLogout}>
          <span>로그아웃</span>
          <span className="m">›</span>
        </button>
      </div>
    </div>
  );
}
