import type { SessionStore } from '@/entities/session';
import type { AuthGateway } from './ports';

export function logout(deps: { auth: AuthGateway; session: SessionStore }): Promise<void> {
  void deps;
  throw new Error('not implemented: logout');
}
