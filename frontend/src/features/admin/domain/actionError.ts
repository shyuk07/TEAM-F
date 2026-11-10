export type ErrorInfo = { status: number; errorCode: string; message: string };

// TODO: 처리 오류는 서버 message(명세 표의 한국어 문구)를 그대로 보여 주고, 없으면 임시 문구를 쓴다.
//   왜: 관리자 화면 오류 문구 정본이 없다 (docs/design/frontend/admin.md D-7)
//   언제: 결정 후 (디자인 시스템: content.md 관리자 오류 문구 확정)
export const ACTION_ERROR_FALLBACK = '처리하지 못했어요. 잠시 후 다시 시도해 주세요.';

export function actionErrorMessage(info: ErrorInfo): string {
  return info.message.trim() !== '' ? info.message : ACTION_ERROR_FALLBACK;
}
