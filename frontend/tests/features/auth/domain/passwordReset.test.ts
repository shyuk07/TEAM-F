import {
  canConfirmReset,
  canRequestReset,
  isResetCode,
} from '@/features/auth/domain/passwordReset';

describe('isResetCode', () => {
  it.each<[string, string, boolean]>([
    ['6자리 숫자', '123456', true],
    ['0으로만 된 6자리', '000000', true],
    ['5자리', '12345', false],
    ['7자리', '1234567', false],
    ['문자 포함', '12a456', false],
    ['빈 값', '', false],
    ['앞 공백 포함', ' 123456', false],
    ['전각 숫자', '１２３４５６', false],
  ])('%s(%j) → %s', (_name, code, expected) => {
    expect(isResetCode(code)).toBe(expected);
  });
});

describe('canRequestReset', () => {
  it.each<[string, boolean]>([
    ['a@b.c', true],
    ['  ', false],
  ])('%j → %s', (email, expected) => {
    expect(canRequestReset(email)).toBe(expected);
  });
});

describe('canConfirmReset', () => {
  it('코드를 보냈고 6자리 코드와 규칙에 맞는 비밀번호면 true', () => {
    expect(canConfirmReset({ codeSent: true, code: '123456', newPassword: 'pw123456' })).toBe(true);
  });

  it('코드를 보내지 않았으면 false', () => {
    expect(canConfirmReset({ codeSent: false, code: '123456', newPassword: 'pw123456' })).toBe(
      false,
    );
  });
});
