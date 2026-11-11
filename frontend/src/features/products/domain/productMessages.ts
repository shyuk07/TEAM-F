import type { PhotoErrorCode } from './productPhoto';

// TODO: 임시 문구다(상품 오류 문구, 빈 상태 문구, 숨기기 거절 안내, 「상품을 찾을 수 없어요.」 등).
//   왜: 정본 문구가 없다 (docs/design/frontend/products.md D-4, D-16)
//   언제: 결정 후 (사용자·디자인 시스템: content.md에 상품 문구 확정)
export const PRODUCT_ERROR_TEXT = {
  nameRequired: '상품명을 입력해 주세요.',
  nameTooLong: '상품명은 200자 이하로 입력해 주세요.',
  priceRequired: '정상 가격을 입력해 주세요.',
  priceRange: '정상 가격은 1원 이상 99,999,999원 이하의 숫자로 입력해 주세요.',
  categoryTooLong: '카테고리는 80자 이하로 입력해 주세요.',
  photoTooLarge: '사진이 5MB보다 커요. 더 작은 사진을 골라 주세요.',
  photoBadType: 'JPG, PNG, WebP 사진만 올릴 수 있어요.',
  openOffer: '진행 중인 할인이 있어 숨길 수 없어요. 판매를 중단한 뒤 다시 숨겨 주세요.',
  storeSuspended: '정지된 상점에서는 상품을 등록할 수 없어요.',
  storeClosed: '폐점한 상점에서는 상품을 다룰 수 없어요.',
  storeNotApproved: '승인되지 않은 상점에는 상품을 등록할 수 없어요.',
  saveFailed: '저장하지 못했어요. 잠시 후 다시 시도해 주세요.',
  notFound: '상품을 찾을 수 없어요.',
  loadFailed: '상품 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.',
} as const;

export const PRODUCT_TEXT = {
  list: {
    add: '+ 상품 등록',
    closeStore: '상점 폐점',
    account: '계정',
    emptyTitle: '아직 등록한 상품이 없어요',
    emptyDescription: '상품을 등록하면 할인을 만들 수 있어요',
    emptyAction: '상품 등록',
    retry: '다시 시도',
  },
  form: { pending: '처리 중…' },
  create: {
    nameLabel: '상품명 *',
    priceLabel: '정상 가격 *',
    categoryLabel: '카테고리',
    descriptionLabel: '설명',
    photoLabel: '상품 사진 (1장)',
    photoHint: '고객 목록 카드와 상세 화면에 이 사진이 보여요. 없으면 기본 그림이 나와요.',
    submitOffer: '등록하고 할인 만들기',
    submitList: '등록만',
  },
  edit: {
    nameLabel: '상품명',
    priceLabel: '정상 가격',
    categoryLabel: '카테고리',
    descriptionLabel: '설명',
    photoLabel: '상품 사진 (1장)',
    save: '저장',
    visibleTitle: '고객에게 보이기',
    visibleChip: '노출 중',
    hiddenChip: '숨김',
    toStore: '매장으로',
    retry: '다시 시도',
    hide: '숨기기',
    show: '다시 보이기',
    hideHint: '숨기면 이 상품으로 새 할인을 올릴 수 없고, 고객 목록에서 이 상품의 할인이 빠져요.',
  },
  photo: {
    camera: '카메라로 찍기',
    album: '앨범에서 고르기',
    retry: '다시 시도',
    pickOther: '다른 사진 고르기',
    cancel: '취소',
    remove: '삭제',
    sheetTitle: '사진 추가',
    sheetHint: 'JPG·PNG·WebP, 5MB 이하',
    empty: '사진 추가 · 카메라 또는 앨범', // 앞의 「+」는 화면에서 따로 그린다
    change: '사진 바꾸기',
    uploading: '올리는 중…',
    removeLink: '사진 삭제',
  },
} as const;

export function photoErrorMessage(code: PhotoErrorCode): string {
  return code === 'TOO_LARGE' ? PRODUCT_ERROR_TEXT.photoTooLarge : PRODUCT_ERROR_TEXT.photoBadType;
}

export function productErrorMessage(
  e: { status: number; errorCode: string; message: string },
  ctx: 'create' | 'save' | 'toggle' | 'load',
): string {
  switch (e.errorCode) {
    case 'IMAGE_TOO_LARGE':
      return PRODUCT_ERROR_TEXT.photoTooLarge;
    case 'UNSUPPORTED_IMAGE_TYPE':
      return PRODUCT_ERROR_TEXT.photoBadType;
    case 'PRODUCT_HAS_OPEN_OFFER':
      if (ctx === 'toggle') return PRODUCT_ERROR_TEXT.openOffer;
      break;
    case 'STORE_SUSPENDED':
      return PRODUCT_ERROR_TEXT.storeSuspended;
    case 'STORE_CLOSED':
      return PRODUCT_ERROR_TEXT.storeClosed;
    case 'STORE_NOT_APPROVED':
      return PRODUCT_ERROR_TEXT.storeNotApproved;
    case 'NETWORK_ERROR':
      return e.message;
  }
  return ctx === 'load' ? PRODUCT_ERROR_TEXT.loadFailed : PRODUCT_ERROR_TEXT.saveFailed;
}

export function productCountLabel(total: number): string {
  return `상품 ${total}개`;
}

export type ProductLoadFailure = { kind: 'notFound' | 'loadFailed'; message: string };

export function productLoadFailure(e: {
  status: number;
  errorCode: string;
  message: string;
}): ProductLoadFailure {
  if (e.status === 404 || e.status === 403) {
    return { kind: 'notFound', message: PRODUCT_ERROR_TEXT.notFound };
  }
  return { kind: 'loadFailed', message: productErrorMessage(e, 'load') };
}
