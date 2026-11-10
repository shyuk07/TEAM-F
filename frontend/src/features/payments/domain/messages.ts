import type { PointInputError } from './point';

export const POINT_INPUT_LABEL = '포인트 사용 (100P 단위)';
export const POINT_ALL_LABEL = '전액';
export const PROCESSING_LABEL = '처리 중…';

// TODO: 포인트 입력 오류 문구는 임시다.
//   왜: content.md에 포인트 입력 오류 문구가 없다 (docs/design/frontend/payments.md D-5)
//   언제: 결정 후 (사용자: 포인트 오류 문구)
export const POINT_NOT_INTEGER_MESSAGE = '숫자로 입력해 주세요.';
export const POINT_NOT_UNIT_MESSAGE = '100P 단위로 입력해 주세요.';
export const POINT_OVER_BALANCE_MESSAGE = '보유 포인트보다 많이 쓸 수 없어요.';
export const POINT_OVER_TOTAL_MESSAGE = '결제 금액보다 많이 쓸 수 없어요.';

// TODO: 서버 message가 비었을 때 보여 줄 결제 오류 대체 문구는 임시다.
//   왜: 화면 명세에 결제 오류 문구가 없어 서버 message를 쓴다 (docs/design/frontend/payments.md D-7)
//   언제: 결정 후 (디자인 시스템: 결제 오류 문구)
export const PAY_FALLBACK_MESSAGE = '결제하지 못했어요. 잠시 후 다시 시도해 주세요.';

export function pointInputMessage(error: PointInputError): string | null {
  switch (error) {
    case 'notInteger':
      return POINT_NOT_INTEGER_MESSAGE;
    case 'notUnit':
      return POINT_NOT_UNIT_MESSAGE;
    case 'overBalance':
      return POINT_OVER_BALANCE_MESSAGE;
    case 'overTotal':
      return POINT_OVER_TOTAL_MESSAGE;
    case null:
      return null;
  }
}

// 결제 409는 error_code가 아니라 HTTP 상태로 분기하고, 문구는 서버 message를 쓴다 (docs/design/frontend/payments.md C-2, D-7)
export function payErrorMessage(e: { status: number; errorCode: string; message: string }): string {
  return e.message !== '' ? e.message : PAY_FALLBACK_MESSAGE;
}
