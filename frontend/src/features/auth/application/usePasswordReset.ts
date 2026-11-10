import type { ErrorInfo } from './errorInfo';

export function usePasswordReset(): {
  sentEmail: string | null;
  request(email: string): Promise<void>;
  resend(): Promise<void>;
  confirm(code: string, newPassword: string): Promise<boolean>;
  invalidate(): void;
  requestPending: boolean;
  requestError: ErrorInfo | null;
  confirmPending: boolean;
  confirmError: ErrorInfo | null;
} {
  throw new Error('not implemented: usePasswordReset');
}
