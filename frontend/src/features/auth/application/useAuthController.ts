import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { SessionStoreToken } from '@/entities/session';
import { useDep } from '@/shared/lib/di';
import type { AuthState } from '../domain/authState';
import type { User } from '../domain/user';
import type { AuthContextValue } from './authContext';
import { login as loginUseCase } from './login';
import { logout as logoutUseCase } from './logout';
import { restoreSession } from './restoreSession';
import { AuthGatewayToken } from './tokens';

// FIXME: 다른 영역 요청이 받은 401·TOKEN_REVOKED를 처리하지 않는다. 화면은 다시 불러오기 전까지 로그인 상태로 남는다.
//   왜: 서버 데이터를 읽는 공용 훅이 아직 없어 401을 세션 정리로 잇는 곳이 없다. 공용 훅이 받은 401에서 SessionStoreToken의 clear()를 부르면 이 컨트롤러가 구독으로 anonymous가 된다 (docs/design/frontend/auth.md §3.2). C8·C9는 유스케이스가 직접 clear()해 처리함 (docs/design/frontend/auth-account.md D-18)
//   언제: products 구현 시(첫 보호 API 화면 O4), 늦어도 배포 전
export function useAuthController(): AuthContextValue {
  const auth = useDep(AuthGatewayToken);
  const session = useDep(SessionStoreToken);
  const [state, setState] = useState<AuthState>(() =>
    session.hasSession() ? { status: 'loading' } : { status: 'anonymous', cause: 'other' },
  );
  const [nonce, setNonce] = useState(0);
  const loggingOut = useRef(false);

  const reload = useCallback(() => {
    setState({ status: 'loading' });
    setNonce((n) => n + 1);
  }, []);

  // 세션 확인: 마운트와 reload()에서만 서버를 부른다.
  useEffect(() => {
    if (nonce === 0 && !session.hasSession()) return;
    const ctrl = new AbortController();
    void restoreSession({ auth, session }, ctrl.signal).then((next) => {
      if (next !== null && !ctrl.signal.aborted) setState(next);
    });
    return () => ctrl.abort();
  }, [auth, session, nonce]);

  // 다른 탭의 변경, 같은 탭의 clear()(401 등)
  useEffect(
    () =>
      session.subscribe((has) => {
        if (loggingOut.current) return;
        if (has) reload();
        else setState({ status: 'anonymous', cause: 'other' });
      }),
    [session, reload],
  );

  const login = useCallback(
    async (email: string, password: string): Promise<User> => {
      const user = await loginUseCase({ auth, session }, { email, password });
      setState({ status: 'authenticated', user });
      return user;
    },
    [auth, session],
  );

  const logout = useCallback(async (): Promise<void> => {
    loggingOut.current = true;
    try {
      await logoutUseCase({ auth, session });
      setState({ status: 'anonymous', cause: 'loggedOut' });
    } finally {
      loggingOut.current = false;
    }
  }, [auth, session]);

  const withdraw = useCallback(async (password: string, signal?: AbortSignal): Promise<void> => {
    void password;
    void signal;
    throw new Error('not implemented: useAuthController.withdraw');
  }, []);

  // 인증 상태일 때만 사용자를 바꾼다. reload()와 달리 loading을 거치지 않는다(auth-account.md D-13).
  const replaceUser = useCallback((user: User): void => {
    setState((prev) =>
      prev.status === 'authenticated' ? { status: 'authenticated', user } : prev,
    );
  }, []);

  return useMemo(
    () => ({ state, login, logout, withdraw, reload, replaceUser }),
    [state, login, logout, withdraw, reload, replaceUser],
  );
}
