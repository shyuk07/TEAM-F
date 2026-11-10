import type { SessionStore } from '@/entities/session';
import type { AuthGateway } from './ports';

export async function logout(deps: { auth: AuthGateway; session: SessionStore }): Promise<void> {
  try {
    await deps.auth.logout();
  } catch {
    // 서버 실패와 관계없이 로컬 세션은 지운다.
  } finally {
    deps.session.clear();
  }
}
