import type { SessionStore } from '@/entities/session';
import type { ProfilePatch } from '../domain/profileInput';
import type { User } from '../domain/user';
import { readErrorInfo } from './errorInfo';
import type { AccountGateway } from './ports';

// 401이면 세션을 지워 인증 상태를 anonymous로 바꾸고(가드가 /login으로 보냄) 같은 오류를 던진다(auth-account.md D-18).
export async function updateProfile(
  deps: { account: AccountGateway; session: SessionStore },
  patch: ProfilePatch,
  signal?: AbortSignal,
): Promise<User> {
  try {
    return await deps.account.updateProfile(patch, signal);
  } catch (e) {
    if (readErrorInfo(e).status === 401) deps.session.clear();
    throw e;
  }
}
