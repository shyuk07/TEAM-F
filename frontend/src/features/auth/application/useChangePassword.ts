import type { PasswordChangeForm } from '../domain/passwordChange';
import type { ErrorInfo } from './errorInfo';

export function useChangePassword(): {
  submit(form: PasswordChangeForm): Promise<boolean>;
  pending: boolean;
  error: ErrorInfo | null;
  done: boolean;
  reset(): void;
} {
  throw new Error('not implemented: useChangePassword');
}
