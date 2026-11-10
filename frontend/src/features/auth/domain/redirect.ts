import type { User } from './user';

export type LoginLocationState = { from: string };

export function isSafeInternalPath(path: string): boolean {
  void path;
  throw new Error('not implemented: isSafeInternalPath');
}

export function readFrom(state: unknown): string | null {
  void state;
  throw new Error('not implemented: readFrom');
}

export function loginRedirectState(
  cause: 'loggedOut' | 'other',
  currentPath: string,
): LoginLocationState | undefined {
  void cause;
  void currentPath;
  throw new Error('not implemented: loginRedirectState');
}

export function resolvePostLoginPath(user: User, from: string | null): string {
  void user;
  void from;
  throw new Error('not implemented: resolvePostLoginPath');
}
