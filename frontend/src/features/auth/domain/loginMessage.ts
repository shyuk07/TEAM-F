export const INVALID_CREDENTIALS_MESSAGE = '이메일 또는 비밀번호가 올바르지 않습니다.';
export const LOGIN_FALLBACK_MESSAGE = '로그인하지 못했어요. 잠시 후 다시 시도해 주세요.';

export function loginErrorMessage(e: { errorCode: string; message: string }): string {
  if (e.errorCode === 'INVALID_CREDENTIALS') return INVALID_CREDENTIALS_MESSAGE;
  return e.message !== '' ? e.message : LOGIN_FALLBACK_MESSAGE;
}

// 세션 확인(restoreSession) 실패 때 서버 문구가 비어 있으면 보여 줄 임시 문구.
export const SESSION_ERROR_FALLBACK_MESSAGE = '불러오지 못했어요. 잠시 후 다시 시도해 주세요.';
