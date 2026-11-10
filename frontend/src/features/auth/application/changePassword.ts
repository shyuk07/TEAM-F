import type { SessionStore } from '@/entities/session';
import type { PasswordChangeForm } from '../domain/passwordChange';
import { readErrorInfo } from './errorInfo';
import type { AccountGateway } from './ports';

// 성공해도 session.clear()를 부르지 않는다: 서버가 현재 토큰을 유지한다(auth-account.md D-9, C-1).
// 401이면 세션을 지우고 같은 오류를 던진다(D-18).
export async function changePassword(
  deps: { account: AccountGateway; session: SessionStore },
  form: PasswordChangeForm,
  signal?: AbortSignal,
): Promise<void> {
  try {
    await deps.account.changePassword(
      { currentPassword: form.current, newPassword: form.next },
      signal,
    );
  } catch (e) {
    if (readErrorInfo(e).status === 401) deps.session.clear();
    throw e;
  }
}
