import type { SessionStore } from '@/entities/session';
import type { User } from '../domain/user';
import type { AuthGateway } from './ports';

export function login(
  deps: { auth: AuthGateway; session: SessionStore },
  input: { email: string; password: string },
): Promise<User> {
  void deps;
  void input;
  throw new Error('not implemented: login');
}
