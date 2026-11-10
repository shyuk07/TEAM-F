export const INVALID_CREDENTIALS_MESSAGE = '이메일 또는 비밀번호가 올바르지 않습니다.';
export const LOGIN_FALLBACK_MESSAGE = '로그인하지 못했어요. 잠시 후 다시 시도해 주세요.';

export function loginErrorMessage(e: { errorCode: string; message: string }): string {
  void e;
  throw new Error('not implemented: loginErrorMessage');
}
