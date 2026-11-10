import type { SessionStore } from '@/entities/session';
import type { PasswordChangeForm } from '../domain/passwordChange';
import type { AccountGateway } from './ports';

export async function changePassword(
  deps: { account: AccountGateway; session: SessionStore },
  form: PasswordChangeForm,
  signal?: AbortSignal,
): Promise<void> {
  void deps;
  void form;
  void signal;
  throw new Error('not implemented: changePassword');
}
