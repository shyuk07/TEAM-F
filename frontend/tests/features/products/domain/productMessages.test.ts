import { describe, expect, it } from 'vitest';
import {
  productCountLabel,
  productErrorMessage,
  productLoadFailure,
} from '@/features/products/domain/productMessages';

const e = (status: number, errorCode: string, message = '') => ({ status, errorCode, message });

const SAVE_DEFAULT = '저장하지 못했어요. 잠시 후 다시 시도해 주세요.';
const LOAD_DEFAULT = '상품 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.';

describe('features/products domain productMessages', () => {
  describe('productErrorMessage', () => {
    it('IMAGE_TOO_LARGE → 정본 5MB 문구', () => {
      expect(productErrorMessage(e(400, 'IMAGE_TOO_LARGE'), 'create')).toBe(
        '사진이 5MB보다 커요. 더 작은 사진을 골라 주세요.',
      );
    });

    it('UNSUPPORTED_IMAGE_TYPE → 형식 문구', () => {
      expect(productErrorMessage(e(400, 'UNSUPPORTED_IMAGE_TYPE'), 'create')).toBe(
        'JPG, PNG, WebP 사진만 올릴 수 있어요.',
      );
    });

    it('PRODUCT_HAS_OPEN_OFFER(toggle) → 숨기기 거절 문구', () => {
      expect(productErrorMessage(e(400, 'PRODUCT_HAS_OPEN_OFFER'), 'toggle')).toBe(
        '진행 중인 할인이 있어 숨길 수 없어요. 판매를 중단한 뒤 다시 숨겨 주세요.',
      );
    });

    it.each([
      ['STORE_SUSPENDED', '정지된 상점에서는 상품을 등록할 수 없어요.'],
      ['STORE_CLOSED', '폐점한 상점에서는 상품을 다룰 수 없어요.'],
      ['STORE_NOT_APPROVED', '승인되지 않은 상점에는 상품을 등록할 수 없어요.'],
    ])('%s → 상점 상태 문구', (code, message) => {
      expect(productErrorMessage(e(400, code), 'create')).toBe(message);
    });

    // A3: 서버 message는 쓰지 않는다
    it('VALIDATION_ERROR(save·create)는 서버 message를 쓰지 않고 공통 문구', () => {
      const msg = '정상 가격은 진행 중인 할인 가격보다 커야 합니다.';
      expect(productErrorMessage(e(400, 'VALIDATION_ERROR', msg), 'save')).toBe(SAVE_DEFAULT);
      expect(productErrorMessage(e(400, 'VALIDATION_ERROR', msg), 'create')).toBe(SAVE_DEFAULT);
    });

    it('VALIDATION_ERROR인데 message가 비면 기본 문구', () => {
      expect(productErrorMessage(e(400, 'VALIDATION_ERROR', ''), 'save')).toBe(SAVE_DEFAULT);
    });

    it('NETWORK_ERROR는 message 그대로', () => {
      expect(productErrorMessage(e(0, 'NETWORK_ERROR', '네트워크가 끊겼어요'), 'save')).toBe(
        '네트워크가 끊겼어요',
      );
    });

    it('모르는 코드 → 기본 문구, load는 불러오기 문구', () => {
      expect(productErrorMessage(e(500, 'UNKNOWN', 'x'), 'save')).toBe(SAVE_DEFAULT);
      expect(productErrorMessage(e(500, 'UNKNOWN', 'x'), 'load')).toBe(LOAD_DEFAULT);
    });
  });

  // C1
  describe('productLoadFailure', () => {
    it.each([404, 403])('status %i → notFound + 「상품을 찾을 수 없어요.」', (status) => {
      expect(productLoadFailure(e(status, 'NOT_FOUND', 'x'))).toEqual({
        kind: 'notFound',
        message: '상품을 찾을 수 없어요.',
      });
    });

    it('500 UNKNOWN → loadFailed + 불러오기 기본 문구', () => {
      expect(productLoadFailure(e(500, 'UNKNOWN', 'x'))).toEqual({
        kind: 'loadFailed',
        message: LOAD_DEFAULT,
      });
    });

    it('NETWORK_ERROR(status 0) → loadFailed, message는 서버가 만든 문구 그대로', () => {
      expect(productLoadFailure(e(0, 'NETWORK_ERROR', '네트워크가 끊겼어요'))).toEqual({
        kind: 'loadFailed',
        message: '네트워크가 끊겼어요',
      });
    });
  });

  describe('productCountLabel', () => {
    it.each([
      [4, '상품 4개'],
      [0, '상품 0개'],
    ])('%i → %s', (total, label) => {
      expect(productCountLabel(total)).toBe(label);
    });
  });
});
