import type { SessionStore } from '@/entities/session';
import type { AccountGateway } from './ports';

export async function requestPasswordReset(
  deps: { account: AccountGateway },
  email: string,
  signal?: AbortSignal,
): Promise<void> {
  await deps.account.requestPasswordReset(email.trim(), signal);
}

// 재설정은 모든 토큰을 무효로 만들므로 성공 뒤 남은 세션을 지운다(REQ-32, auth-account.md D-10).
export async function confirmPasswordReset(
  deps: { account: AccountGateway; session: SessionStore },
  input: { email: string; code: string; newPassword: string },
  signal?: AbortSignal,
): Promise<void> {
  await deps.account.confirmPasswordReset(input, signal);
  deps.session.clear();
}
