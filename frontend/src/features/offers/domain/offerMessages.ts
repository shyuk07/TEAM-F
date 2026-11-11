import type { RadiusKm } from './nearbyQuery';

// 정본 문구 (wireframe.html·screens.md, customer-home.md §3.1)
export const NEARBY_EMPTY_TITLE = '근처에 마감 할인이 없어요';
export const NEARBY_EMPTY_HINT = '반경을 넓히거나 저녁 시간에 다시 확인해 보세요.';
export const LOCATION_SHEET_TITLE = '어디서 찾을까요?';
export const USE_CURRENT_LOCATION_LABEL = '◎ 현재 위치 사용';
export const LOCATION_DENIED_HINT = '위치를 허용하지 않으면 거리 없이 전체 할인을 보여 줘요.';
export const OWNER_APPLY_LINK = '사장님이신가요? 입점 신청';
export const LOAD_MORE_LABEL = '더 보기';
export const SEARCH_LABEL = '상품명 검색';

export function widenRadiusLabel(r: RadiusKm): string {
  return `반경 ${r}km로 넓히기`;
}

// TODO: 임시 문구다(목록 불러오기 실패, 정렬 묶음 이름). 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/customer-home.md §3.1)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export const OFFERS_LOAD_FAILED_MESSAGE = '불러오지 못했어요. 잠시 후 다시 시도해 주세요.';
export const SORT_GROUP_LABEL = '정렬';

// TODO: C2 오류·없음 문구를 임시로 정했다.
//   왜: C2 전용 문구 정본이 없다 (docs/design/frontend/offers.md D-8)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export const OFFER_DETAIL_LOAD_FAILED_MESSAGE = '할인 정보를 불러오지 못했어요.';
export const OFFER_NOT_FOUND_MESSAGE = '할인을 찾을 수 없어요.';
export const MAX_PER_RESERVATION_TEXT = '한 번에 최대 5개까지 예약할 수 있어요.';
export const PRODUCT_IMAGE_PLACEHOLDER = '상품 이미지';
export const PICKUP_TIME_LABEL = '픽업 시간';
export const CANCEL_DEADLINE_LABEL = '취소 가능';
