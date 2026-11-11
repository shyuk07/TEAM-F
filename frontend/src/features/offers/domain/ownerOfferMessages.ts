import type { ErrorInfo } from '@/shared/lib/errorInfo';

export const OWNER_OFFER_MESSAGES = {
  EMPTY_ON_SALE: '판매 중인 할인이 없어요.',
  EMPTY_SCHEDULED: '판매 예정인 할인이 없어요.',
  EMPTY_SOLD_OUT: '품절된 할인이 없어요.',
  EMPTY_CLOSED: '판매 종료된 할인이 없어요.',
  LOAD_FAILED: '할인 목록을 불러오지 못했어요.',
  LOAD_OFFER_FAILED: '할인 정보를 불러오지 못했어요.',
  RETRY: '다시 시도',
  EDIT_LOCKED_NOTICE: '예약이 있는 할인은 수정할 수 없어요. 판매를 중단하고 다시 올려 주세요.',
} as const;

export function ownerOfferErrorMessage(info: ErrorInfo): string {
  switch (info.errorCode) {
    case 'STORE_SUSPENDED':
      return '상점이 정지되어 할인을 변경할 수 없어요.';
    case 'STORE_CLOSED':
      return '상점이 폐점 상태예요.';
    case 'PRODUCT_INACTIVE':
      return '판매가 중단된 상품이에요.';
    case 'OFFER_ALREADY_OPEN':
      return '이 상품에 이미 진행 중인 할인이 있어요.';
    case 'OFFER_SUSPENDED':
      return '관리자에 의해 정지된 할인이에요.';
    case 'OFFER_CLOSED':
      return '이미 종료되거나 중단된 할인이에요.';
    case 'OFFER_HAS_RESERVATIONS':
      return '예약이 있는 할인은 수정할 수 없어요. 판매를 중단하고 다시 올려 주세요.';
    case 'INSUFFICIENT_STOCK':
      return '남은 재고보다 많이 뺄 수 없어요.';
    case 'PICKED_UP_RESERVATION_EXISTS':
      return '이미 픽업 완료된 예약이 있어 일괄 취소할 수 없어요.';
    case 'VALIDATION_ERROR':
      return '입력값을 다시 확인해 주세요.';
    default:
      return '요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.';
  }
}
