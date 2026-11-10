import type { SessionStore } from '@/entities/session';
import type { AccountGateway } from './ports';

export async function requestPasswordReset(
  deps: { account: AccountGateway },
  email: string,
  signal?: AbortSignal,
): Promise<void> {
  void deps;
  void email;
  void signal;
  throw new Error('not implemented: requestPasswordReset');
}

export async function confirmPasswordReset(
  deps: { account: AccountGateway; session: SessionStore },
  input: { email: string; code: string; newPassword: string },
  signal?: AbortSignal,
): Promise<void> {
  void deps;
  void input;
  void signal;
  throw new Error('not implemented: confirmPasswordReset');
}
