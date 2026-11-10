import {
  ACCOUNT_FALLBACK_MESSAGE,
  PASSWORD_BLANK_MESSAGE,
  PASSWORD_TOO_LONG_MESSAGE,
  changePasswordErrorView,
  passwordRuleMessage,
  resetConfirmErrorMessage,
  signupErrorView,
  withdrawErrorView,
} from '@/features/auth/domain/accountMessages';
import type { PasswordCheck } from '@/features/auth/domain/passwordRule';

describe('signupErrorView', () => {
  it('EMAIL_DUPLICATED면 서버 문구와 관계없이 이메일 칸에 정본 문구', () => {
    expect(signupErrorView({ errorCode: 'EMAIL_DUPLICATED', message: '아무 서버 문구' })).toEqual({
      field: 'email',
      message: '이미 가입된 이메일입니다.',
    });
  });

  it('VALIDATION_ERROR면 폼 오류 자리에 서버 문구', () => {
    expect(
      signupErrorView({
        errorCode: 'VALIDATION_ERROR',
        message: '이메일 형식이 올바르지 않습니다.',
      }),
    ).toEqual({ field: 'form', message: '이메일 형식이 올바르지 않습니다.' });
  });

  it('NETWORK_ERROR면 폼 오류 자리에 그 문구', () => {
    expect(signupErrorView({ errorCode: 'NETWORK_ERROR', message: '네트워크 문구' })).toEqual({
      field: 'form',
      message: '네트워크 문구',
    });
  });

  it('message가 비면 폼 오류 자리에 기본 문구', () => {
    expect(signupErrorView({ errorCode: 'INTERNAL_ERROR', message: '' })).toEqual({
      field: 'form',
      message: ACCOUNT_FALLBACK_MESSAGE,
    });
  });
});

describe('resetConfirmErrorMessage', () => {
  it('INVALID_RESET_CODE면 서버 문구 대신 화면 정본 문구', () => {
    expect(
      resetConfirmErrorMessage({
        errorCode: 'INVALID_RESET_CODE',
        message: '재설정 코드가 올바르지 않거나 만료되었습니다.',
      }),
    ).toBe('코드가 맞지 않거나 만료됐어요. 코드를 다시 받아 주세요.');
  });

  it('VALIDATION_ERROR면 서버 문구', () => {
    expect(
      resetConfirmErrorMessage({ errorCode: 'VALIDATION_ERROR', message: '서버 규칙 문구' }),
    ).toBe('서버 규칙 문구');
  });

  it('message가 비면 기본 문구', () => {
    expect(resetConfirmErrorMessage({ errorCode: 'INTERNAL_ERROR', message: '' })).toBe(
      ACCOUNT_FALLBACK_MESSAGE,
    );
  });
});

describe('changePasswordErrorView', () => {
  it('CURRENT_PASSWORD_MISMATCH면 현재 비밀번호 칸에 화면 정본 문구', () => {
    expect(
      changePasswordErrorView({
        errorCode: 'CURRENT_PASSWORD_MISMATCH',
        message: '현재 비밀번호가 올바르지 않습니다.',
      }),
    ).toEqual({ field: 'current', message: '현재 비밀번호가 일치하지 않습니다.' });
  });

  it('VALIDATION_ERROR면 폼 오류 자리에 서버 문구', () => {
    expect(
      changePasswordErrorView({ errorCode: 'VALIDATION_ERROR', message: '서버 규칙 문구' }),
    ).toEqual({ field: 'form', message: '서버 규칙 문구' });
  });

  it('403 FORBIDDEN이면 폼 오류 자리에 서버 문구', () => {
    expect(
      changePasswordErrorView({ errorCode: 'FORBIDDEN', message: '정지된 계정입니다.' }),
    ).toEqual({ field: 'form', message: '정지된 계정입니다.' });
  });
});

describe('withdrawErrorView (C7, customer-home §3.1)', () => {
  it('FORBIDDEN이면 폼 오류 자리에 서버 문구', () => {
    expect(withdrawErrorView({ errorCode: 'FORBIDDEN', message: '정지된 계정입니다.' })).toEqual({
      field: 'form',
      message: '정지된 계정입니다.',
    });
  });

  it('서버 문구가 비어 있으면 폼 오류 자리에 기본 문구', () => {
    expect(withdrawErrorView({ errorCode: 'DATA_INCONSISTENT', message: '' })).toEqual({
      field: 'form',
      message: ACCOUNT_FALLBACK_MESSAGE,
    });
  });
});

describe('passwordRuleMessage', () => {
  it.each<[PasswordCheck, string | null]>([
    ['blank', PASSWORD_BLANK_MESSAGE],
    ['tooLong', PASSWORD_TOO_LONG_MESSAGE],
    ['tooShort', null],
    ['empty', null],
    ['ok', null],
  ])('%s → %j', (check, expected) => {
    expect(passwordRuleMessage(check)).toBe(expected);
  });
});
