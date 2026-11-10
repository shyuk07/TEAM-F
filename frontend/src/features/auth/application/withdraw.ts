import type { SessionStore } from '@/entities/session';
import type { AccountGateway } from './ports';

export function withdrawAccount(
  deps: { account: AccountGateway; session: SessionStore },
  password: string,
  signal?: AbortSignal,
): Promise<void> {
  void deps;
  void password;
  void signal;
  throw new Error('not implemented: withdrawAccount');
}
