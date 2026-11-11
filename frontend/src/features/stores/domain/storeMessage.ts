// TODO: 임시 문구다(개설·폐점 실패 기본 문구, 서버 메시지 그대로 표시, O7 「뒤로」). 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/stores.md D-10, D-11)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export const GEOCODING_UNAVAILABLE_MESSAGE =
  '지금은 주소를 확인할 수 없어요. 잠시 후 다시 시도해 주세요.';

const OPEN_STORE_FALLBACK_MESSAGE = '상점을 열지 못했어요. 잠시 후 다시 시도해 주세요.';
const CLOSE_STORE_FALLBACK_MESSAGE = '상점을 폐점하지 못했어요. 잠시 후 다시 시도해 주세요.';

type ErrorInput = { status: number; errorCode: string; message: string };

// 분기는 errorCode(또는 status 503). 503만 정본 문구, 그 밖은 서버 message(비면 기본 문구)(F11, D-10).
export function openStoreErrorMessage(info: ErrorInput): string {
  if (info.errorCode === 'GEOCODING_UNAVAILABLE' || info.status === 503) {
    return GEOCODING_UNAVAILABLE_MESSAGE;
  }
  return info.message !== '' ? info.message : OPEN_STORE_FALLBACK_MESSAGE;
}

export function closeStoreErrorMessage(info: ErrorInput): string {
  return info.message !== '' ? info.message : CLOSE_STORE_FALLBACK_MESSAGE;
}
