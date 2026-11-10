import { useDep } from '@/shared/lib/di';
import type { SignupForm } from '../domain/signupInput';
import { useAuth } from './authContext';
import type { ErrorInfo } from './errorInfo';
import { signupAndLogin, type SignupOutcome } from './signup';
import { AccountGatewayToken } from './tokens';
import { useSubmit } from './useSubmit';

// 결과만 돌려준다. 이동은 page가 한다(로그인 성공은 인증 상태 변화로, 로그인 실패는 onLoginFailed로).
export function useSignup(): {
  submit(form: SignupForm): Promise<SignupOutcome | undefined>;
  pending: boolean;
  error: ErrorInfo | null;
} {
  const account = useDep(AccountGatewayToken);
  const { login } = useAuth();
  const { state, submit } = useSubmit<SignupForm, SignupOutcome>((form, signal) =>
    signupAndLogin({ account, login }, form, signal),
  );
  return { submit, pending: state.pending, error: state.error };
}
