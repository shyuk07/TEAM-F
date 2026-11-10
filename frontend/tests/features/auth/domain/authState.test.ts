import { decideAccess, type AuthState } from '@/features/auth/domain/authState';
import { adminUser, customerUser, ownerUser } from '../fakes/users';

describe('decideAccess(state, "OWNER")', () => {
  it.each<[string, AuthState, string]>([
    ['loading', { status: 'loading' }, 'loading'],
    ['anonymous other', { status: 'anonymous', cause: 'other' }, 'login'],
    ['anonymous loggedOut', { status: 'anonymous', cause: 'loggedOut' }, 'login-without-from'],
    ['error', { status: 'error', errorCode: 'NETWORK_ERROR', message: 'm' }, 'error'],
    ['OWNER APPROVED', { status: 'authenticated', user: ownerUser }, 'allow'],
    [
      'OWNER PENDING',
      { status: 'authenticated', user: { ...ownerUser, status: 'PENDING' } },
      'allow',
    ],
    [
      'OWNER SUSPENDED',
      { status: 'authenticated', user: { ...ownerUser, status: 'SUSPENDED' } },
      'allow',
    ],
    ['CUSTOMER', { status: 'authenticated', user: customerUser }, 'home'],
    ['ADMIN', { status: 'authenticated', user: adminUser }, 'home'],
  ])('%s → %s', (_name, state, expected) => {
    expect(decideAccess(state, 'OWNER')).toBe(expected);
  });
});
