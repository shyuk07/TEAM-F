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

// C7 정본 문구(screens.md C7). 서버 문구·C9 문구와 다르다.
export const WITHDRAW_PASSWORD_MISMATCH_MESSAGE = '비밀번호가 일치하지 않습니다.';

// TODO: 임시 문구다(탈퇴 예약 줄, 포인트 빈·실패, 다시 시도). 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/customer-home.md §3.1)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export const WITHDRAW_RESERVATIONS_TEXT = '모두 취소·환불';
export const POINTS_EMPTY_MESSAGE = '포인트 내역이 없어요';
export const POINTS_LOAD_FAILED_MESSAGE = '불러오지 못했어요. 잠시 후 다시 시도해 주세요.';
export const RETRY_LABEL = '다시 시도';

export function withdrawErrorView(e: ErrorLike): FieldError<'password' | 'form'> {
  if (e.errorCode === 'CURRENT_PASSWORD_MISMATCH') {
    return { field: 'password', message: WITHDRAW_PASSWORD_MISMATCH_MESSAGE };
  }
  return { field: 'form', message: accountErrorMessage(e) };
}

export function signupErrorView(e: ErrorLike): FieldError<'email' | 'form'> {
  if (e.errorCode === 'EMAIL_DUPLICATED') {
    return { field: 'email', message: EMAIL_DUPLICATED_MESSAGE };
  }
  return { field: 'form', message: accountErrorMessage(e) };
}

export function resetConfirmErrorMessage(e: ErrorLike): string {
  if (e.errorCode === 'INVALID_RESET_CODE') return INVALID_RESET_CODE_MESSAGE;
  return accountErrorMessage(e);
}

export function changePasswordErrorView(e: ErrorLike): FieldError<'current' | 'form'> {
  if (e.errorCode === 'CURRENT_PASSWORD_MISMATCH') {
    return { field: 'current', message: CURRENT_PASSWORD_MISMATCH_MESSAGE };
  }
  return { field: 'form', message: accountErrorMessage(e) };
}

// 계정·보안 서버 오류는 서버 문구(합니다체)를 그대로 보인다(content.md). 비어 있으면 기본 문구.
export function accountErrorMessage(e: ErrorLike): string {
  return e.message !== '' ? e.message : ACCOUNT_FALLBACK_MESSAGE;
}

// 'tooShort'는 라벨 「(8자 이상)」이 알려 주므로 문구 없이 버튼만 비활성으로 둔다.
export function passwordRuleMessage(check: PasswordCheck): string | null {
  if (check === 'blank') return PASSWORD_BLANK_MESSAGE;
  if (check === 'tooLong') return PASSWORD_TOO_LONG_MESSAGE;
  return null;
}
