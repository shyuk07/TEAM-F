import type { SessionStore } from '@/entities/session';
import type { AccountGateway } from './ports';

export async function requestPasswordReset(
  deps: { account: AccountGateway },
  email: string,
): Promise<void> {
  void deps;
  void email;
  throw new Error('not implemented: requestPasswordReset');
}

export async function confirmPasswordReset(
  deps: { account: AccountGateway; session: SessionStore },
  input: { email: string; code: string; newPassword: string },
): Promise<void> {
  void deps;
  void input;
  throw new Error('not implemented: confirmPasswordReset');
}
