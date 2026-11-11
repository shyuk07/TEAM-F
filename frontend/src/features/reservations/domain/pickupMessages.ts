// TODO: 빈 상태·오류 문구가 임시다
//   왜: content.md에 정본이 없다 (owner-today.md Q-4)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export const PICKUP_MESSAGES = {
  EMPTY_WAITING: '픽업 대기 중인 예약이 없어요.',
  EMPTY_DONE: '오늘 완료된 픽업이 없어요.',
  LOAD_FAILED: '예약 목록을 불러오지 못했어요.',
  RETRY: '다시 시도',
  CODE_MISMATCH: '코드가 맞지 않아요. 다시 확인해 주세요.',
  DEFAULT_ERROR: '요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.',
} as const;

export type ErrorInfo = {
  errorCode?: string;
  status?: number;
  message?: string;
};

export function pickupErrorMessage(info: ErrorInfo): string {
  switch (info.errorCode) {
    case 'PICKUP_CODE_MISMATCH':
      return PICKUP_MESSAGES.CODE_MISMATCH;
    case 'PICKUP_OUTSIDE_WINDOW':
      return '픽업 가능 시간이 아니에요.';
    case 'RESERVATION_ALREADY_PICKED_UP':
      return '이미 픽업이 완료된 예약이에요.';
    case 'RESERVATION_INVALID_STATE':
      return '픽업할 수 없는 상태의 예약이에요.';
    default:
      return info.message || PICKUP_MESSAGES.DEFAULT_ERROR;
  }
}
