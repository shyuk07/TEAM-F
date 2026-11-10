import { SessionStoreToken } from '@/entities/session';
import { useDep } from '@/shared/lib/di';
import type { PasswordChangeForm } from '../domain/passwordChange';
import { changePassword } from './changePassword';
import type { ErrorInfo } from './errorInfo';
import { AccountGatewayToken } from './tokens';
import { useSubmit } from './useSubmit';

// 성공해도 인증 상태·세션은 그대로다(auth-account.md D-9).
export function useChangePassword(): {
  submit(form: PasswordChangeForm): Promise<boolean>;
  pending: boolean;
  error: ErrorInfo | null;
  done: boolean;
  reset(): void;
} {
  const account = useDep(AccountGatewayToken);
  const session = useDep(SessionStoreToken);
  const { state, submit, reset } = useSubmit<PasswordChangeForm, true>(async (form, signal) => {
    await changePassword({ account, session }, form, signal);
    return true;
  });
  const submitForm = async (form: PasswordChangeForm): Promise<boolean> =>
    (await submit(form)) === true;
  return {
    submit: submitForm,
    pending: state.pending,
    error: state.error,
    done: state.done,
    reset,
  };
}
