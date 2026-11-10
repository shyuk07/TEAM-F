import { canSubmitLogin } from '@/features/auth/domain/loginInput';

describe('canSubmitLogin', () => {
  it.each<[string, string, boolean]>([
    ['a@b.c', 'pw', true],
    ['', 'pw', false],
    ['   ', 'pw', false],
    ['a@b.c', '', false],
    ['a@b.c', '  ', true],
  ])('(%j, %j) → %s', (email, password, expected) => {
    expect(canSubmitLogin(email, password)).toBe(expected);
  });
});
