import type { PasswordCheck } from './passwordRule';

export type ErrorLike = { errorCode: string; message: string };

export type FieldError<F extends string> = { field: F; message: string };

// 정본 문구
export const EMAIL_DUPLICATED_MESSAGE = '이미 가입된 이메일입니다.';
export const INVALID_RESET_CODE_MESSAGE = '코드가 맞지 않거나 만료됐어요. 코드를 다시 받아 주세요.';
export const CURRENT_PASSWORD_MISMATCH_MESSAGE = '현재 비밀번호가 일치하지 않습니다.';
export const PASSWORD_RESET_DONE_NOTICE = '새 비밀번호로 로그인하세요';
export const PROFILE_SAVED_NOTICE = '저장했어요';

// TODO: 임시 문구다(비밀번호 변경 완료, 비밀번호 공백·길이 초과, 확인 불일치, 가입 뒤 로그인 실패, 계정 처리 기본 문구, 「뒤로」). 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/auth-account.md D-12, D-14, D-20, D-25)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export const PASSWORD_CHANGED_NOTICE = '비밀번호를 바꿨어요.';
export const PASSWORD_BLANK_MESSAGE = '비밀번호는 공백만으로 만들 수 없어요.';
export const PASSWORD_TOO_LONG_MESSAGE = '비밀번호가 너무 길어요. 72바이트 이하로 줄여 주세요.';
export const PASSWORD_CONFIRM_MISMATCH_MESSAGE = '새 비밀번호가 서로 달라요. 다시 확인해 주세요.';
export const SIGNUP_LOGIN_FAILED_NOTICE = '가입했어요. 로그인해 주세요.';
export const ACCOUNT_FALLBACK_MESSAGE = '처리하지 못했어요. 잠시 후 다시 시도해 주세요.';
export const BACK_LABEL = '뒤로';

export function signupErrorView(e: ErrorLike): FieldError<'email' | 'form'> {
  void e;
  throw new Error('not implemented: signupErrorView');
}

export function resetConfirmErrorMessage(e: ErrorLike): string {
  void e;
  throw new Error('not implemented: resetConfirmErrorMessage');
}

export function changePasswordErrorView(e: ErrorLike): FieldError<'current' | 'form'> {
  void e;
  throw new Error('not implemented: changePasswordErrorView');
}

export function accountErrorMessage(e: ErrorLike): string {
  void e;
  throw new Error('not implemented: accountErrorMessage');
}

export function passwordRuleMessage(check: PasswordCheck): string | null {
  void check;
  throw new Error('not implemented: passwordRuleMessage');
}
