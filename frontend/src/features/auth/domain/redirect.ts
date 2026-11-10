import { ROUTES } from '@/shared/lib/routes';
import { isOwnerPath, type User } from './user';

export type LoginNotice = 'passwordReset' | 'signupLoginFailed';

// A1 진입 안내 한 줄의 진입 경로(customer-home.md D-7)
export type LoginEntry = 'reservation' | 'customerTab';

export type LoginLocationState = { from?: string; notice?: LoginNotice; entry?: LoginEntry };

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

const LOGIN_NOTICES: readonly LoginNotice[] = ['passwordReset', 'signupLoginFailed'];

export function readLoginNotice(state: unknown): LoginNotice | null {
  if (typeof state !== 'object' || state === null) return null;
  const notice = (state as { notice?: unknown }).notice;
  return LOGIN_NOTICES.find((n) => n === notice) ?? null;
}

export function readLoginEntry(state: unknown): LoginEntry | null {
  void state;
  throw new Error('not implemented: readLoginEntry');
}

export function isAccountPath(path: string): boolean {
  return path === ROUTES.account || path.startsWith(`${ROUTES.account}/`);
}

export function loginRedirectState(
  cause: 'loggedOut' | 'other',
  currentPath: string,
  entry?: LoginEntry,
): LoginLocationState | undefined {
  void entry;
  return cause === 'loggedOut' ? undefined : { from: currentPath };
}

export function resolvePostLoginPath(user: User, from: string | null): string {
  const safe = from !== null && isSafeInternalPath(from) ? from : null;
  // C8·C9는 역할 무관 화면이라 세션이 끊겨 다시 로그인하면 역할과 관계없이 그 화면으로 돌아간다(auth-account.md D-29).
  if (safe !== null && isAccountPath(safe)) return safe;
  // TODO: 상점주는 항상 O1로, 관리자는 홈으로 보낸다.
  //   왜: 상점 유무로 O0·O1을 정하는 stores 영역과 관리자 셸(M1)이 아직 없다 (docs/design/frontend/auth.md C-3, D-6)
  //   언제: stores 구현 시, admin 구현 시
  if (user.role === 'OWNER') return safe !== null && isOwnerPath(safe) ? safe : ROUTES.ownerToday;
  if (user.role === 'CUSTOMER') return safe !== null && !isOwnerPath(safe) ? safe : ROUTES.home;
  return ROUTES.home;
}
