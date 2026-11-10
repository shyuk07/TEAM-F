import { ROUTES } from '@/shared/lib/routes';
import { isAdminPath, isOwnerPath, type User } from './user';

export type LoginLocationState = { from: string };

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

export function loginRedirectState(
  cause: 'loggedOut' | 'other',
  currentPath: string,
): LoginLocationState | undefined {
  return cause === 'loggedOut' ? undefined : { from: currentPath };
}

export function resolvePostLoginPath(user: User, from: string | null): string {
  const safe = from !== null && isSafeInternalPath(from) ? from : null;
  // TODO: 상점주는 항상 O1로 보낸다.
  //   왜: 상점 유무로 O0·O1을 정하는 stores 영역이 아직 없다 (docs/design/frontend/auth.md C-3, D-6)
  //   언제: stores 구현 시
  if (user.role === 'OWNER') return safe !== null && isOwnerPath(safe) ? safe : ROUTES.ownerToday;
  // 관리자는 M1으로, 관리자 화면에서 로그인으로 왔으면 그 화면으로 (docs/design/frontend/admin.md D-10)
  if (user.role === 'ADMIN')
    return safe !== null && isAdminPath(safe) ? safe : ROUTES.adminApprovals;
  return safe !== null && !isOwnerPath(safe) && !isAdminPath(safe) ? safe : ROUTES.home;
}
