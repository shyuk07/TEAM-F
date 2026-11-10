import type { Role, User } from './user';

export type AuthState =
  | { status: 'loading' }
  | { status: 'anonymous'; cause: 'loggedOut' | 'other' }
  | { status: 'authenticated'; user: User }
  | { status: 'error'; errorCode: string; message: string };

export type AccessDecision =
  'loading' | 'allow' | 'login' | 'login-without-from' | 'home' | 'error';

export function decideAccess(state: AuthState, required: Role | 'ANY'): AccessDecision {
  switch (state.status) {
    case 'loading':
      return 'loading';
    case 'error':
      return 'error';
    case 'anonymous':
      return state.cause === 'loggedOut' ? 'login-without-from' : 'login';
    case 'authenticated':
      return state.user.role === required ? 'allow' : 'home';
  }
}
