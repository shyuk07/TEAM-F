import { createContext, useContext } from 'react';
import type { AuthState } from '../domain/authState';
import type { User } from '../domain/user';

export type AuthContextValue = {
  state: AuthState;
  login(email: string, password: string): Promise<User>;
  logout(): Promise<void>;
  // 성공하면 로그아웃과 같은 상태(anonymous loggedOut)가 된다(customer-home.md D-24).
  withdraw(password: string, signal?: AbortSignal): Promise<void>;
  reload(): void;
  replaceUser(user: User): void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('AuthProvider 밖에서 useAuth를 호출했습니다.');
  return value;
}
