import { useAuth } from './authContext';
import type { ErrorInfo } from './errorInfo';
import { useSubmit } from './useSubmit';

// 성공하면 인증 상태가 anonymous(loggedOut)가 되어 고객 가드가 C1로 보낸다(customer-home.md D-24).
export function useWithdraw(): {
  submit(password: string): Promise<boolean>;
  pending: boolean;
  error: ErrorInfo | null;
} {
  const { withdraw } = useAuth();
  const { state, submit } = useSubmit<string, true>(async (password, signal) => {
    await withdraw(password, signal);
    return true;
  });
  return {
    submit: async (password: string) => (await submit(password)) === true,
    pending: state.pending,
    error: state.error,
  };
}
