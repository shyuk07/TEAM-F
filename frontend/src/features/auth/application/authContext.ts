import { createContext } from 'react';
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
  throw new Error('not implemented: useAuth');
}
