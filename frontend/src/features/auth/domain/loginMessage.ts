import { PASSWORD_RESET_DONE_NOTICE, SIGNUP_LOGIN_FAILED_NOTICE } from './accountMessages';
import type { LoginEntry, LoginNotice } from './redirect';

export const INVALID_CREDENTIALS_MESSAGE = '이메일 또는 비밀번호가 올바르지 않습니다.';
export const LOGIN_FALLBACK_MESSAGE = '로그인하지 못했어요. 잠시 후 다시 시도해 주세요.';

export function loginErrorMessage(e: { errorCode: string; message: string }): string {
  if (e.errorCode === 'INVALID_CREDENTIALS') return INVALID_CREDENTIALS_MESSAGE;
  return e.message !== '' ? e.message : LOGIN_FALLBACK_MESSAGE;
}

// A1 진입 안내 한 줄(A3 재설정 완료, A2 가입 뒤 로그인 실패, auth-account.md D-10·D-25).
export function loginNoticeMessage(notice: LoginNotice): string {
  return notice === 'passwordReset' ? PASSWORD_RESET_DONE_NOTICE : SIGNUP_LOGIN_FAILED_NOTICE;
}

const LOGIN_ENTRY_RESERVATION_MESSAGE = '예약을 이어가려면 로그인하세요.';
// TODO: 내 예약·마이 진입 안내의 끝맺음을 임시로 정했다.
//   왜: 정본(screens.md A1 동작 메모)은 「예약 내역을 보려면…」까지만 있다 (docs/design/frontend/customer-home.md C-7, Q-11)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
const LOGIN_ENTRY_CUSTOMER_TAB_MESSAGE = '예약 내역을 보려면 로그인하세요.';

// A1 진입 경로별 안내 한 줄(customer-home.md §3.1, D-7)
export function loginEntryMessage(entry: LoginEntry): string {
  return entry === 'reservation'
    ? LOGIN_ENTRY_RESERVATION_MESSAGE
    : LOGIN_ENTRY_CUSTOMER_TAB_MESSAGE;
}

// 세션 확인(restoreSession) 실패 때 서버 문구가 비어 있으면 보여 줄 임시 문구.
export const SESSION_ERROR_FALLBACK_MESSAGE = '불러오지 못했어요. 잠시 후 다시 시도해 주세요.';
