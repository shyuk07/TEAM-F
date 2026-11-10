import { describe, expect, it } from 'vitest';
import {
  GEOCODING_UNAVAILABLE_MESSAGE,
  closeStoreErrorMessage,
  openStoreErrorMessage,
} from '@/features/stores/domain/storeMessage';

describe('features/stores domain openStoreErrorMessage', () => {
  it('GEOCODING_UNAVAILABLE(503)은 서버 문구가 아니라 정본 문구를 돌려준다', () => {
    const msg = openStoreErrorMessage({
      status: 503,
      errorCode: 'GEOCODING_UNAVAILABLE',
      message: '서버 문구',
    });
    expect(msg).toBe(GEOCODING_UNAVAILABLE_MESSAGE);
    expect(msg).toBe('지금은 주소를 확인할 수 없어요. 잠시 후 다시 시도해 주세요.');
  });

  it.each([
    ['ADDRESS_NOT_FOUND', '주소를 찾을 수 없습니다'],
    ['STORE_DUPLICATED', '중복된 상점입니다'],
    ['STORE_ALREADY_EXISTS', '이미 상점이 있어요'],
    ['VALIDATION_ERROR', '형식이 올바르지 않아요'],
  ])('개설 %s이면 message를 그대로 돌려준다', (errorCode, message) => {
    expect(openStoreErrorMessage({ status: 400, errorCode, message })).toBe(message);
  });

  it('개설 오류의 message가 빈 문자열이면 기본 문구를 돌려준다', () => {
    expect(openStoreErrorMessage({ status: 400, errorCode: 'STORE_DUPLICATED', message: '' })).toBe(
      '상점을 열지 못했어요. 잠시 후 다시 시도해 주세요.',
    );
  });
});

describe('features/stores domain closeStoreErrorMessage', () => {
  it.each([
    ['STORE_HAS_OPEN_OFFERS', '진행 중인 할인이 있어요'],
    ['STORE_HAS_RESERVED_RESERVATIONS', '픽업 대기 중인 예약이 있어요'],
    ['STORE_ALREADY_CLOSED', '이미 폐점된 상점입니다'],
    ['STORE_SUSPENDED', '정지된 상점이에요'],
    ['FORBIDDEN', '권한이 없어요'],
  ])('폐점 %s이면 message를 그대로 돌려준다', (errorCode, message) => {
    expect(closeStoreErrorMessage({ status: 400, errorCode, message })).toBe(message);
  });

  it('폐점 오류의 message가 빈 문자열이면 기본 문구를 돌려준다', () => {
    expect(
      closeStoreErrorMessage({ status: 400, errorCode: 'STORE_HAS_OPEN_OFFERS', message: '' }),
    ).toBe('상점을 폐점하지 못했어요. 잠시 후 다시 시도해 주세요.');
  });
});
