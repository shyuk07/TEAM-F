import { useEffect } from 'react';
import { SessionStoreToken } from '@/entities/session';
import { onAuthFailure } from '@/shared/api/authFailure';
import { useDep } from '@/shared/lib/di';

// 401·TOKEN_REVOKED 감지를 세션 정리로 잇는 브리지(D-9). clear()가 구독을 불러
// useAuthController가 anonymous로 바뀌고 가드가 A1로 보낸다(stores.md §2.2).
export function AuthFailureBridge() {
  const sessionStore = useDep(SessionStoreToken);

  useEffect(() => {
    return onAuthFailure(() => {
      // 세션이 남아 있을 때만 정리한다. 연속된 실패 이벤트는 첫 clear() 뒤 세션이 없어 무시되고,
      // 재로그인 뒤의 새 만료는 다시 정리된다. 한계: 재로그인 직후 옛 토큰 요청의 늦은 401이 새 세션을 지울 수 있다.
      if (!sessionStore.hasSession()) return;
      sessionStore.clear();
    });
  }, [sessionStore]);

  return null;
}
