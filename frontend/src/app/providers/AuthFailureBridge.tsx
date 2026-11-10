import { useEffect } from 'react';
import { SessionStoreToken } from '@/entities/session';
import { onAuthFailure } from '@/shared/api/authFailure';
import { useDep } from '@/shared/lib/di';

// 401·TOKEN_REVOKED 감지를 세션 정리로 잇는 브리지(D-9). clear()가 구독을 불러
// useAuthController가 anonymous로 바뀌고 가드가 A1로 보낸다(stores.md §2.2).
export function AuthFailureBridge() {
  const sessionStore = useDep(SessionStoreToken);

  useEffect(() => {
    let cleared = false;
    return onAuthFailure(() => {
      // 연속된 실패 이벤트에도 세션 정리는 1회만 실행한다.
      if (cleared) return;
      cleared = true;
      sessionStore.clear();
    });
  }, [sessionStore]);

  return null;
}
