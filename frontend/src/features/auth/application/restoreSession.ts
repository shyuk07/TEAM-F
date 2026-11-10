import type { SessionStore } from '@/entities/session';
import type { AuthState } from '../domain/authState';
import { readErrorInfo } from './errorInfo';
import type { AuthGateway } from './ports';

export async function restoreSession(
  deps: { auth: AuthGateway; session: SessionStore },
  signal: AbortSignal,
): Promise<AuthState | null> {
  if (!deps.session.hasSession()) return { status: 'anonymous', cause: 'other' };
  try {
    const user = await deps.auth.findMe(signal);
    return signal.aborted ? null : { status: 'authenticated', user };
  } catch (e) {
    if (signal.aborted) return null;
    const info = readErrorInfo(e);
    if (info.status === 401 || info.status === 403) {
      // TODO: /users/me가 403이면 로그인 실패로 처리한다. 정지 상점주는 로그인 응답이 200이어도 들어올 수 없다.
      //   왜: 정지 계정은 내 정보를 조회할 수 없다 (docs/design/frontend/auth.md C-2, D-4)
      //   언제: 결정 후 (백엔드: 정지 상점주의 /users/me 허용 여부)
      deps.session.clear();
      return { status: 'anonymous', cause: 'other' };
    }
    // 일시 장애로 로그아웃시키지 않는다.
    return { status: 'error', errorCode: info.errorCode, message: info.message };
  }
}
