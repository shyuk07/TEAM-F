import {
  isAccountPath,
  isSafeInternalPath,
  loginRedirectState,
  readFrom,
  readLoginNotice,
  resolvePostLoginPath,
} from '@/features/auth/domain/redirect';
import type { Role, User } from '@/features/auth/domain/user';
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

describe('isSafeInternalPath 제어문자·역슬래시', () => {
  it.each(['/\t/evil.com', '/\n/evil.com', '/\\evil.com', '/a\u0000b', '/a\u007fb'])(
    '%j는 거부한다',
    (path) => {
      expect(isSafeInternalPath(path)).toBe(false);
    },
  );

  it('정상 경로는 통과한다', () => {
    expect(isSafeInternalPath('/owner/offers?page=2')).toBe(true);
  });
});

describe('readLoginNotice', () => {
  it.each<[string, unknown, string | null]>([
    ['passwordReset', { notice: 'passwordReset' }, 'passwordReset'],
    ['signupLoginFailed', { notice: 'signupLoginFailed' }, 'signupLoginFailed'],
    ['알 수 없는 notice', { notice: 'x' }, null],
    ['null', null, null],
    ['notice 없음', { from: '/' }, null],
  ])('%s → %j', (_name, state, expected) => {
    expect(readLoginNotice(state)).toBe(expected);
  });
});

describe('isAccountPath', () => {
  it.each<[string, boolean]>([
    ['/account/profile', true],
    ['/account', true],
    ['/accountx', false],
  ])('%s → %s', (path, expected) => {
    expect(isAccountPath(path)).toBe(expected);
  });
});

describe('resolvePostLoginPath: /account/* 복귀(역할 무관)', () => {
  it.each<[string, string, User]>([
    ['OWNER', '/account/password', ownerUser],
    ['CUSTOMER', '/account/profile', customerUser],
    ['ADMIN', '/account/profile', adminUser],
  ])('%s + from %s → 그대로', (_name, from, user) => {
    expect(resolvePostLoginPath(user, from)).toBe(from);
  });
});

describe('readFrom: notice가 함께 있어도', () => {
  it('from만 읽는다', () => {
    expect(readFrom({ from: '/owner/offers', notice: 'passwordReset' })).toBe('/owner/offers');
  });
});
