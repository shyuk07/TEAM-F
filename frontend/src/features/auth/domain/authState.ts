import type { Role, User } from './user';

export type AuthState =
  | { status: 'loading' }
  | { status: 'anonymous'; cause: 'loggedOut' | 'other' }
  | { status: 'authenticated'; user: User }
  | { status: 'error'; errorCode: string; message: string };

export type AccessDecision =
  'loading' | 'allow' | 'login' | 'login-without-from' | 'home' | 'error';

export function decideAccess(state: AuthState, required: Role): AccessDecision {
  void state;
  void required;
  throw new Error('not implemented: decideAccess');
}
