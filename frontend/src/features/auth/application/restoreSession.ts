import type { SessionStore } from '@/entities/session';
import type { AuthState } from '../domain/authState';
import type { AuthGateway } from './ports';

export function restoreSession(
  deps: { auth: AuthGateway; session: SessionStore },
  signal: AbortSignal,
): Promise<AuthState | null> {
  void deps;
  void signal;
  throw new Error('not implemented: restoreSession');
}
