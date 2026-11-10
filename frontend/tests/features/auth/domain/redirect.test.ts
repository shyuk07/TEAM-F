import {
  isSafeInternalPath,
  loginRedirectState,
  readFrom,
  resolvePostLoginPath,
} from '@/features/auth/domain/redirect';
import type { Role } from '@/features/auth/domain/user';
import { ROUTES } from '@/shared/lib/routes';
import { adminUser, customerUser, ownerUser } from '../fakes/users';

describe('isSafeInternalPath', () => {
  it.each(['/owner/today', '/', '/owner/offers?x=1#a'])('%s는 안전하다', (path) => {
    expect(isSafeInternalPath(path)).toBe(true);
  });

  it.each(['//evil.com', '/\\evil', 'https://evil.com', 'owner/today', '', '/login', '/login?x=1'])(
    '%j는 안전하지 않다',
    (path) => {
      expect(isSafeInternalPath(path)).toBe(false);
    },
  );
});

describe('readFrom', () => {
  it('안전한 from이 있으면 그 값을 돌려준다', () => {
    expect(readFrom({ from: '/owner/offers' })).toBe('/owner/offers');
  });

  it.each([
    ['null', null],
    ['undefined', undefined],
    ['문자열', 'x'],
    ['숫자 from', { from: 1 }],
    ['외부 주소 from', { from: '//evil.com' }],
  ])('%s이면 null이다', (_name, state) => {
    expect(readFrom(state)).toBeNull();
  });
});

describe('resolvePostLoginPath', () => {
  const as = (role: Role) =>
    role === 'OWNER' ? ownerUser : role === 'CUSTOMER' ? customerUser : adminUser;

  it.each<[Role, string | null, string]>([
    ['OWNER', null, ROUTES.ownerToday],
    ['OWNER', '/owner/offers', '/owner/offers'],
    ['OWNER', '/owner', '/owner'],
    ['OWNER', '/', ROUTES.ownerToday],
    ['OWNER', '/ownerx', ROUTES.ownerToday],
    ['CUSTOMER', null, ROUTES.home],
    ['CUSTOMER', '/offers/1', '/offers/1'],
    ['CUSTOMER', '/owner/today', ROUTES.home],
    ['ADMIN', '/owner/today', ROUTES.home],
    ['OWNER', '//evil.com', ROUTES.ownerToday],
  ])('%s + from %j → %s', (role, from, expected) => {
    expect(resolvePostLoginPath(as(role), from)).toBe(expected);
  });
});

describe('loginRedirectState', () => {
  it('other면 현재 경로를 from으로 담는다', () => {
    expect(loginRedirectState('other', '/owner/offers?x=1')).toEqual({ from: '/owner/offers?x=1' });
  });

  it('loggedOut이면 undefined다', () => {
    expect(loginRedirectState('loggedOut', '/owner/today')).toBeUndefined();
  });
});
