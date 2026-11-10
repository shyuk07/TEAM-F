import { ROUTES } from '@/shared/lib/routes';
import { isOwnerPath, type User } from './user';

export type LoginNotice = 'passwordReset' | 'signupLoginFailed';

export type LoginLocationState = { from?: string; notice?: LoginNotice };

function hasControlChar(text: string): boolean {
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    if (c <= 0x1f || c === 0x7f) return true;
  }
  return false;
}

// 내부 경로만 허용한다(open redirect, 로그인 화면 무한 이동 방지).
export function isSafeInternalPath(path: string): boolean {
  if (!path.startsWith('/')) return false;
  if (path.startsWith('//') || path.startsWith('/\\')) return false;
  if (path.includes('://')) return false;
  // 브라우저는 URL에서 탭·개행을 지우므로 `/\t/evil.com`이 `//evil.com`이 된다.
  if (hasControlChar(path) || path.includes('\\')) return false;
  const pathname = path.split(/[?#]/, 1)[0];
  return pathname !== ROUTES.login;
}

export function readFrom(state: unknown): string | null {
  if (typeof state !== 'object' || state === null) return null;
  const from = (state as { from?: unknown }).from;
  return typeof from === 'string' && isSafeInternalPath(from) ? from : null;
}

export function readLoginNotice(state: unknown): LoginNotice | null {
  void state;
  throw new Error('not implemented: readLoginNotice');
}

export function isAccountPath(path: string): boolean {
  void path;
  throw new Error('not implemented: isAccountPath');
}

export function loginRedirectState(
  cause: 'loggedOut' | 'other',
  currentPath: string,
): LoginLocationState | undefined {
  return cause === 'loggedOut' ? undefined : { from: currentPath };
}

export function resolvePostLoginPath(user: User, from: string | null): string {
  const safe = from !== null && isSafeInternalPath(from) ? from : null;
  // TODO: 상점주는 항상 O1로, 관리자는 홈으로 보낸다.
  //   왜: 상점 유무로 O0·O1을 정하는 stores 영역과 관리자 셸(M1)이 아직 없다 (docs/design/frontend/auth.md C-3, D-6)
  //   언제: stores 구현 시, admin 구현 시
  if (user.role === 'OWNER') return safe !== null && isOwnerPath(safe) ? safe : ROUTES.ownerToday;
  if (user.role === 'CUSTOMER') return safe !== null && !isOwnerPath(safe) ? safe : ROUTES.home;
  return ROUTES.home;
}
