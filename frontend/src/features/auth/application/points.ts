import type { SessionStore } from '@/entities/session';
import type { PointPage } from '../domain/points';
import { readErrorInfo } from './errorInfo';
import type { AccountGateway } from './ports';

// 401이면 세션을 지워 인증 상태를 anonymous로 바꾸고(가드가 /login으로 보냄) 같은 오류를 던진다(auth-account.md D-18).
export async function loadPoints(
  deps: { account: AccountGateway; session: SessionStore },
  query: { page: number; size: number },
  signal?: AbortSignal,
): Promise<PointPage> {
  try {
    return await deps.account.findPoints(query, signal);
  } catch (e) {
    if (readErrorInfo(e).status === 401) deps.session.clear();
    throw e;
  }
}
