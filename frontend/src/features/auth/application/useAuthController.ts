import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { SessionStoreToken } from '@/entities/session';
import { useDep } from '@/shared/lib/di';
import type { AuthState } from '../domain/authState';
import type { User } from '../domain/user';
import type { AuthContextValue } from './authContext';
import { login as loginUseCase } from './login';
import { logout as logoutUseCase } from './logout';
import { restoreSession } from './restoreSession';
import { AccountGatewayToken, AuthGatewayToken } from './tokens';
import { withdrawAccount } from './withdraw';

export function useAuthController(): AuthContextValue {
  const auth = useDep(AuthGatewayToken);
  const account = useDep(AccountGatewayToken);
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

  // 성공 → 로그아웃과 같은 상태(C7 → C1). 401로 세션이 지워졌으면 anonymous(other), 그 외 실패는 상태 그대로(customer-home.md D-24).
  const withdraw = useCallback(
    async (password: string, signal?: AbortSignal): Promise<void> => {
      loggingOut.current = true;
      try {
        await withdrawAccount({ account, session }, password, signal);
        setState({ status: 'anonymous', cause: 'loggedOut' });
      } catch (e) {
        if (!session.hasSession()) setState({ status: 'anonymous', cause: 'other' });
        throw e;
      } finally {
        loggingOut.current = false;
      }
    },
    [account, session],
  );

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
