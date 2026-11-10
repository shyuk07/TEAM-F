import type { SessionStore } from '@/entities/session';
import type { User } from '../domain/user';
import type { AuthGateway } from './ports';

export async function login(
  deps: { auth: AuthGateway; session: SessionStore },
  input: { email: string; password: string },
): Promise<User> {
  const { accessToken } = await deps.auth.login(input.email, input.password);
  // findMe가 클라이언트의 토큰 헤더를 쓰므로 저장이 먼저다.
  deps.session.save(accessToken);
  try {
    // TODO: /users/me가 403이면 로그인 실패로 처리한다. 정지 상점주는 로그인 응답이 200이어도 들어올 수 없다.
    //   왜: 정지 계정은 내 정보를 조회할 수 없다 (docs/design/frontend/auth.md C-2, D-4)
    //   언제: 결정 후 (백엔드: 정지 상점주의 /users/me 허용 여부)
    return await deps.auth.findMe();
  } catch (e) {
    // 토큰만 남은 반쪽 로그인 상태를 만들지 않는다.
    deps.session.clear();
    throw e;
  }
}
