import { useAuth } from './authContext';
import type { ErrorInfo } from './errorInfo';
import { useSubmit } from './useSubmit';

export type WithdrawController = {
  submit(password: string): Promise<boolean>;
  pending: boolean;
  error: ErrorInfo | null;
};

// 성공하면 인증 상태가 anonymous(loggedOut)가 되어 고객 가드가 C1로 보낸다(customer-home.md D-24).
// 탈퇴는 되돌릴 수 없어 언마운트 abort signal을 넘기지 않는다. 언마운트 뒤 상태 갱신만 useSubmit이 막는다(customer-home.md D-32).
export function useWithdraw(): WithdrawController {
  const { withdraw } = useAuth();
  const { state, submit } = useSubmit<string, true>(async (password) => {
    await withdraw(password);
    return true;
  });
  return {
    submit: async (password: string) => (await submit(password)) === true,
    pending: state.pending,
    error: state.error,
  };
}
