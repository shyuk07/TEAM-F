// 문구 정본 위치: docs/design/frontend/reservations.md §3.1
export const RESERVE_CONTINUE_LABEL = '결제 이어하기';
// TODO: 결제 대기 중복 문구는 임시다(screens.md C2의 「오류 예시」 표기를 뺀 문구).
//   왜: 화면 명세가 예시로만 적었다 (docs/design/frontend/reservations.md D-13)
//   언제: 결정 후 (디자인 시스템: C2 중복 예약 문구)
export const PENDING_EXISTS_MESSAGE = '이 상품에 결제하지 않은 예약이 이미 있어요.';
export const TAB_ACTIVE_LABEL = '진행 중';
export const TAB_PAST_LABEL = '지난 예약';
export const CANCEL_LINK_LABEL = '예약 취소';
export const PICKUP_CODE_LABEL = '매장에서 보여 주세요';
export const PROCESSING_LABEL = '처리 중…';
export const EMPTY_ACTION_LABEL = '할인 보러 가기';
// TODO: 내 예약 빈 상태 본문과 목록 오류 재시도 버튼 문구는 임시다.
//   왜: screens.md E1에 내 예약 빈 상태 본문·재시도 문구 정본이 없다 (docs/design/frontend/reservations.md D-15, D-17, C-7)
//   언제: 결정 후 (디자인 시스템: E1 문구)
export const EMPTY_ACTIVE_MESSAGE = '진행 중인 예약이 없어요.';
export const EMPTY_PAST_MESSAGE = '지난 예약이 없어요.';
export const RETRY_LABEL = '다시 시도';
export const CANCEL_SHEET_BACK_LABEL = '돌아가기';
export const CANCEL_SHEET_CONFIRM_LABEL = '예약 취소';
export const REFUND_AMOUNT_LABEL = '돌려받는 금액';
// TODO: C5a 환불 안내를 숫자 대신 문구로 보여 준다. 환불액·포인트 복구·회수 숫자 표시 방식을 정하면 바꾼다.
//   왜: 예약 응답에 결제 금액·사용 포인트·적립 포인트가 없다 (docs/design/frontend/reservations.md D-14, C-6)
//   언제: 결정 후 (사용자: C5a 환불 표시)
export const REFUND_NOTICE =
  '결제한 금액은 전액 환불되고, 사용한 포인트는 돌려드리며 적립된 포인트는 회수돼요.';
export const DIRECTIONS_LABEL = '길찾기';
export const MY_RESERVATIONS_LINK_LABEL = '내 예약 보기';
// TODO: 시트 제목(C5a·C3a)과 결제 대기 예약 취소 안내는 임시 문구다.
//   왜: screens.md C5a·C3a에 시트 제목이 없고, 결제 대기 취소 안내는 설계 제안값이다 (docs/design/frontend/reservations.md §3.3)
//   언제: 결정 후 (디자인 시스템: C5a·C3a 문구)
export const CANCEL_SHEET_TITLE = '예약을 취소할까요?';
export const LEAVE_SHEET_TITLE = '결제를 그만둘까요?';
export const PENDING_REFUND_NOTICE = '결제 전이라 돌려받을 금액이 없어요.';
export const LEAVE_CONTINUE_LABEL = '결제 계속하기';
export const LEAVE_CANCEL_LABEL = '예약 취소하고 나가기';
export const LEAVE_PAY_LATER_LABEL = '나중에 결제 (내 예약에 남음)';

// TODO: 서버 message가 비었을 때 보여 줄 대체 문구는 임시다.
//   왜: 화면 명세에 예약 오류 문구가 없어 서버 message를 쓴다 (docs/design/frontend/reservations.md D-16)
//   언제: 결정 후 (디자인 시스템: 예약 오류 문구)
export const ERROR_FALLBACK_MESSAGE = '처리하지 못했어요. 잠시 후 다시 시도해 주세요.';

function serverMessage(e: { message: string }): string {
  return e.message !== '' ? e.message : ERROR_FALLBACK_MESSAGE;
}

export function cancelErrorMessage(e: { errorCode: string; message: string }): string {
  return serverMessage(e);
}

export function reserveErrorMessage(e: { errorCode: string; message: string }): string {
  if (e.errorCode === 'PENDING_RESERVATION_EXISTS') return PENDING_EXISTS_MESSAGE;
  return serverMessage(e);
}
