import type { SessionStore } from '@/entities/session';
import { readErrorInfo } from './errorInfo';
import type { AccountGateway } from './ports';

// 성공하면 세션을 지운다. 401도 세션을 지우고 던진다. 그 외(400·403·500)는 세션을 두고 던진다(customer-home.md §3.2).
export async function withdrawAccount(
  deps: { account: AccountGateway; session: SessionStore },
  password: string,
  signal?: AbortSignal,
): Promise<void> {
  try {
    await deps.account.withdraw(password, signal);
  } catch (e) {
    if (readErrorInfo(e).status === 401) deps.session.clear();
    throw e;
  }
  deps.session.clear();
}
