import {
  INVALID_CREDENTIALS_MESSAGE,
  LOGIN_FALLBACK_MESSAGE,
  loginErrorMessage,
} from '@/features/auth/domain/loginMessage';

describe('loginErrorMessage', () => {
  it('INVALID_CREDENTIALS는 서버 문구가 무엇이든 화면 명세 문구로 고정한다', () => {
    expect(loginErrorMessage({ errorCode: 'INVALID_CREDENTIALS', message: '아무 문구' })).toBe(
      '이메일 또는 비밀번호가 올바르지 않습니다.',
    );
    expect(INVALID_CREDENTIALS_MESSAGE).toBe('이메일 또는 비밀번호가 올바르지 않습니다.');
  });

  it('ACCOUNT_LOCKED는 서버 문구를 그대로 쓴다', () => {
    expect(loginErrorMessage({ errorCode: 'ACCOUNT_LOCKED', message: '잠긴 계정입니다.' })).toBe(
      '잠긴 계정입니다.',
    );
  });

  it('FORBIDDEN(정지)은 서버 문구를 그대로 쓴다', () => {
    expect(loginErrorMessage({ errorCode: 'FORBIDDEN', message: '정지된 계정입니다.' })).toBe(
      '정지된 계정입니다.',
    );
  });

  it('NETWORK_ERROR는 그 문구를 쓴다', () => {
    expect(loginErrorMessage({ errorCode: 'NETWORK_ERROR', message: '네트워크 문구' })).toBe(
      '네트워크 문구',
    );
  });

  it('message가 비어 있으면 어떤 코드든 기본 문구를 쓴다', () => {
    expect(loginErrorMessage({ errorCode: 'UNKNOWN', message: '' })).toBe(LOGIN_FALLBACK_MESSAGE);
    expect(loginErrorMessage({ errorCode: 'ACCOUNT_LOCKED', message: '' })).toBe(
      LOGIN_FALLBACK_MESSAGE,
    );
  });
});
