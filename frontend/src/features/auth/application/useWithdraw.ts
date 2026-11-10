import type { ErrorInfo } from './errorInfo';

export function useWithdraw(): {
  submit(password: string): Promise<boolean>;
  pending: boolean;
  error: ErrorInfo | null;
} {
  throw new Error('not implemented: useWithdraw');
}
