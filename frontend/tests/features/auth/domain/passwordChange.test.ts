import {
  canSubmitPasswordChange,
  isConfirmMismatch,
  type PasswordChangeForm,
} from '@/features/auth/domain/passwordChange';

describe('isConfirmMismatch', () => {
  it.each<[string, string, boolean]>([
    ['abcdefgh', '', false],
    ['abcdefgh', 'abcdefgx', true],
    ['abcdefgh', 'abcdefgh', false],
  ])('(%j, %j) → %s', (next, confirm, expected) => {
    expect(isConfirmMismatch(next, confirm)).toBe(expected);
  });
});

describe('canSubmitPasswordChange', () => {
  const valid: PasswordChangeForm = { current: 'old12345', next: 'new12345', confirm: 'new12345' };

  it.each<[string, Partial<PasswordChangeForm>, boolean]>([
    ['유효', {}, true],
    ['현재 비밀번호 빈 값', { current: '' }, false],
    ['새 비밀번호 7자', { next: '1234567', confirm: '1234567' }, false],
    ['확인이 다름', { confirm: 'new12346' }, false],
    ['확인 빈 값', { confirm: '' }, false],
  ])('%s → %s', (_name, override, expected) => {
    expect(canSubmitPasswordChange({ ...valid, ...override })).toBe(expected);
  });
});
