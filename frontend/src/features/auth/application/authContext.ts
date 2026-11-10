import { createContext, useContext } from 'react';
import type { AuthState } from '../domain/authState';
import type { User } from '../domain/user';

export type AuthContextValue = {
  state: AuthState;
  login(email: string, password: string): Promise<User>;
  logout(): Promise<void>;
  reload(): void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('AuthProvider 밖에서 useAuth를 호출했습니다.');
  return value;
}
